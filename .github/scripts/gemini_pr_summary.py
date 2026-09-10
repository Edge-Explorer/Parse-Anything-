from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request


def get_git_diff() -> str:
    """Fetch git diff against origin/main."""
    try:
        # Fetch origin main to ensure accurate diff
        subprocess.run(["git", "fetch", "origin", "main"], check=False, capture_output=True)
        res = subprocess.run(
            ["git", "diff", "origin/main...HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        diff = res.stdout.strip()
        # Cap diff at 40k chars to stay comfortably within context
        if len(diff) > 40000:
            diff = diff[:40000] + "\n\n... [Diff truncated for summary] ..."
        return diff
    except Exception as e:
        print(f"Failed to extract git diff: {e}")
        return ""


def call_gemini(api_key: str, pr_title: str, pr_body: str, diff: str) -> str:
    """Call Google Gemini 2.5 Flash API via REST."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    prompt = f"""You are an automated code intelligence assistant for an open-source library named universal-doc-parser.
Summarize the following Pull Request based on its title, description, and git diff.

PR Title: {pr_title}
PR Description: {pr_body or "No description provided."}

Git Diff:
{diff}

Format your output strictly in Markdown with these exact sections:
### PR Summary by Gemini 2.5 Flash

**Objective:**
[1 concise sentence explaining the primary purpose in plain, clear language]

**Key Changes:**
- [Bullet 1: Main code or configuration modification]
- [Bullet 2: Specific extractor or pipeline update]
- [Bullet 3: Testing or documentation alignment]

**System Impact:**
[1 sentence on memory bounds (<250MB RSS), test suite status, or API backward compatibility]

Rules:
- Do not use emojis anywhere.
- Be concise, professional, and technically accurate.
- Do not invent changes not present in the diff.
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 800,
        },
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as e:
        # If gemini-2.5-flash endpoint is not yet live on user's API tier, fallback to gemini-2.0-flash / gemini-1.5-flash
        print(f"Gemini 2.5 Flash HTTP Error: {e.code}, attempting fallback to gemini-2.0-flash...")
        fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        req_fallback = urllib.request.Request(
            fallback_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req_fallback, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as fallback_err:
            print(f"Gemini fallback failed: {fallback_err}")
            raise


def post_github_comment(github_token: str, repo: str, pr_number: int, comment_body: str) -> None:
    """Post or update comment on the Pull Request."""
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "universal-doc-parser-ci",
    }

    # 1. Fetch existing comments to prevent duplicate spam
    list_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    req_list = urllib.request.Request(list_url, headers=headers, method="GET")

    existing_comment_id = None
    try:
        with urllib.request.urlopen(req_list, timeout=15) as resp:
            comments = json.loads(resp.read().decode("utf-8"))
            for c in comments:
                if "### PR Summary by Gemini" in c.get("body", ""):
                    existing_comment_id = c["id"]
                    break
    except Exception as e:
        print(f"Warning: Could not fetch existing comments: {e}")

    # 2. Update existing comment or create new one
    payload = json.dumps({"body": comment_body}).encode("utf-8")
    if existing_comment_id:
        url = f"https://api.github.com/repos/{repo}/issues/comments/{existing_comment_id}"
        req = urllib.request.Request(url, data=payload, headers=headers, method="PATCH")
    else:
        url = list_url
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

    with urllib.request.urlopen(req, timeout=15) as resp:
        print(f"Successfully posted PR summary (status: {resp.status})")


def main() -> None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY environment variable not set. Skipping PR summary.")
        sys.exit(0)

    github_token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    event_path = os.environ.get("GITHUB_EVENT_PATH")

    if not (github_token and repo and event_path):
        print("Missing required GitHub Actions environment variables.")
        sys.exit(0)

    try:
        with open(event_path, encoding="utf-8") as f:
            event_data = json.load(f)
    except Exception as e:
        print(f"Failed to read event path: {e}")
        sys.exit(0)

    pr_data = event_data.get("pull_request")
    if not pr_data:
        print("Event is not a pull request. Exiting.")
        sys.exit(0)

    pr_number = pr_data["number"]
    pr_title = pr_data.get("title", "")
    pr_body = pr_data.get("body", "")

    print(f"Generating summary for PR #{pr_number}: {pr_title}...")
    diff = get_git_diff()
    if not diff:
        print("No git diff detected. Skipping summary.")
        sys.exit(0)

    try:
        summary = call_gemini(api_key, pr_title, pr_body, diff)
        post_github_comment(github_token, repo, pr_number, summary)
    except Exception as e:
        print(f"Error during Gemini PR summarization: {e}")
        # Don't fail the CI job if summary fails
        sys.exit(0)


if __name__ == "__main__":
    main()
