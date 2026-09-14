from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request


def get_git_diff(base_branch: str = "main", head_ref: str | None = None) -> str:
    """Fetch git diff against base branch."""
    try:
        subprocess.run(["git", "fetch", "origin", base_branch], check=False, capture_output=True)
        target = f"origin/{base_branch}...HEAD"
        if head_ref:
            subprocess.run(["git", "fetch", "origin", head_ref], check=False, capture_output=True)
            target = f"origin/{base_branch}...origin/{head_ref}"

        res = subprocess.run(
            ["git", "diff", target],
            capture_output=True,
            text=True,
            check=True,
        )
        diff = res.stdout.strip()
        # Cap diff at 45k chars to stay comfortably within context
        if len(diff) > 45000:
            diff = diff[:45000] + "\n\n... [Diff truncated for summary] ..."
        return diff
    except Exception as e:
        print(f"Failed to extract git diff: {e}")
        return ""


def call_gemini(api_key: str, pr_title: str, pr_body: str, diff: str) -> str:
    """Call Google Gemini 2.5 Flash API with fallback to Gemini 2.0 Flash."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    prompt = f"""You are an expert automated code intelligence and review assistant for universal-doc-parser (a high-performance, lightweight Python document parsing engine).
Analyze and explain the following Pull Request based on its title, description, and git diff.

PR Title: {pr_title}
PR Description: {pr_body or "No description provided."}

Git Diff:
{diff}

Your goal is to provide a comprehensive, highly clear, and technically precise code review that any developer or user can easily read and understand.
Format your output strictly in GitHub Markdown with these exact sections:

### PR Detailed Review & Summary by Gemini Code Intelligence

#### 1. Executive Summary (In Plain English)
[Provide 2-3 clear, jargon-free sentences explaining exactly what this PR accomplishes, why it was created, and what user problem it solves.]

#### 2. Root Cause Analysis (What Was Broken or Missing?)
[Explain in simple terms what was happening before this PR. If this fixes a bug, explain why the bug occurred (e.g., edge cases, false positive triggers, blur/noise degradation). If a new feature, explain the architectural need.]

#### 3. Step-by-Step Technical Solution
[Detail the exact algorithmic, mathematical, or architectural mechanism implemented to fix the issue or add the feature. Explain why this approach was chosen.]

#### 4. File-by-File Breakdown
| File | Action | Purpose & Key Implementation Details |
| :--- | :--- | :--- |
| `path/to/file` | `Modified` / `New` | [Clear explanation of what changed in this file] |

#### 5. Verification & Test Coverage
- **Unit & Regression Tests:** [Explain what tests were added or executed]
- **Benchmark / Quality Impact:** [Explain metrics like TEDS, CER, WER, or latency improvements]
- **Memory & Resource Budget:** [Memory RSS impact, ensuring <250MB RSS budget]

#### 6. Merge Readiness & Risk Assessment
- **Breaking Changes:** None / Listed
- **Backward Compatibility:** [Explain compatibility]
- **Recommendation:** [Clear statement on readiness to merge]

Rules:
- Do not use emojis anywhere in the output.
- Write in a clear, professional, accessible tone that balances simplicity with deep technical accuracy.
- Ensure all file paths and symbols are wrapped in backticks.
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2500,
        },
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as e:
        print(f"Gemini 2.5 Flash HTTP Error: {e.code}, attempting fallback to gemini-2.0-flash...")
        fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        req_fallback = urllib.request.Request(
            fallback_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req_fallback, timeout=40) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as fallback_err:
            print(f"Gemini fallback failed: {fallback_err}")
            raise


def post_github_comment(github_token: str, repo: str, pr_number: int, comment_body: str) -> None:
    """Post or update review comment on the Pull Request."""
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "universal-doc-parser-ci",
    }

    list_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    req_list = urllib.request.Request(list_url, headers=headers, method="GET")

    existing_comment_id = None
    try:
        with urllib.request.urlopen(req_list, timeout=15) as resp:
            comments = json.loads(resp.read().decode("utf-8"))
            for c in comments:
                if "### PR Detailed Review & Summary by Gemini" in c.get(
                    "body", ""
                ) or "### PR Summary by Gemini" in c.get("body", ""):
                    existing_comment_id = c["id"]
                    break
    except Exception as e:
        print(f"Warning: Could not fetch existing comments: {e}")

    payload = json.dumps({"body": comment_body}).encode("utf-8")
    if existing_comment_id:
        url = f"https://api.github.com/repos/{repo}/issues/comments/{existing_comment_id}"
        req = urllib.request.Request(url, data=payload, headers=headers, method="PATCH")
    else:
        url = list_url
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

    with urllib.request.urlopen(req, timeout=15) as resp:
        print(f"Successfully posted PR review summary (status: {resp.status})")


def main() -> None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY environment variable not set. Skipping PR review.")
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

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "universal-doc-parser-ci",
    }

    # Handle pull_request event or issue_comment event
    pr_number = None
    pr_title = ""
    pr_body = ""
    base_branch = "main"
    head_ref = None

    if "pull_request" in event_data:
        pr_data = event_data["pull_request"]
        pr_number = pr_data["number"]
        pr_title = pr_data.get("title", "")
        pr_body = pr_data.get("body", "")
        base_branch = pr_data.get("base", {}).get("ref", "main")
        head_ref = pr_data.get("head", {}).get("ref")
    elif "issue" in event_data and event_data.get("issue", {}).get("pull_request"):
        pr_number = event_data["issue"]["number"]
        pr_title = event_data["issue"].get("title", "")
        pr_body = event_data["issue"].get("body", "")
        # Fetch PR details to get base and head branch names
        try:
            pr_api_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
            req_pr = urllib.request.Request(pr_api_url, headers=headers, method="GET")
            with urllib.request.urlopen(req_pr, timeout=15) as resp:
                pr_info = json.loads(resp.read().decode("utf-8"))
                base_branch = pr_info.get("base", {}).get("ref", "main")
                head_ref = pr_info.get("head", {}).get("ref")
        except Exception as e:
            print(f"Could not fetch PR info from API: {e}")

    if not pr_number:
        print("Event is not a Pull Request. Exiting.")
        sys.exit(0)

    print(
        f"Generating detailed code review for PR #{pr_number}: {pr_title} (base: {base_branch}, head: {head_ref})..."
    )
    diff = get_git_diff(base_branch, head_ref)
    if not diff:
        print("No git diff detected. Skipping review.")
        sys.exit(0)

    try:
        summary = call_gemini(api_key, pr_title, pr_body, diff)
        post_github_comment(github_token, repo, pr_number, summary)
    except Exception as e:
        print(f"Error during Gemini PR review: {e}")
        sys.exit(0)


if __name__ == "__main__":
    main()
