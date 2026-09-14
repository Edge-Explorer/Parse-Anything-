from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request


def get_diff_from_github_api(repo: str, pr_number: int, github_token: str) -> str:
    """Fetch PR diff directly from GitHub API using the diff media type."""
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.diff",
        "User-Agent": "universal-doc-parser-ci",
    }
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            diff_text = resp.read().decode("utf-8", errors="replace").strip()
            if diff_text:
                if len(diff_text) > 45000:
                    diff_text = diff_text[:45000] + "\n\n... [Diff truncated for summary] ..."
                return diff_text
    except Exception as e:
        print(f"GitHub API diff fetch failed: {e}")
    return ""


def get_git_diff_local(base_branch: str = "main", head_ref: str | None = None) -> str:
    """Fallback local git diff against base branch."""
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
        if len(diff) > 45000:
            diff = diff[:45000] + "\n\n... [Diff truncated for summary] ..."
        return diff
    except Exception as e:
        print(f"Local git diff extraction failed: {e}")
        return ""


def get_pr_diff(
    repo: str,
    pr_number: int,
    github_token: str,
    base_branch: str = "main",
    head_ref: str | None = None,
) -> str:
    """Get PR diff, prioritizing GitHub API with local git fallback."""
    diff = get_diff_from_github_api(repo, pr_number, github_token)
    if not diff:
        diff = get_git_diff_local(base_branch, head_ref)
    return diff


def call_gemini_api(api_key: str, prompt: str) -> str:
    """Call Google Gemini API with fallback models."""
    models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 3500,
        },
    }
    data_bytes = json.dumps(payload).encode("utf-8")

    last_err = None
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            print(f"Gemini model {model} HTTP Error {e.code}: {e.reason}")
            last_err = e
            continue
        except Exception as e:
            print(f"Gemini model {model} failed: {e}")
            last_err = e
            continue

    raise RuntimeError(f"All Gemini models failed. Last error: {last_err}")


def generate_pr_top_summary(api_key: str, pr_title: str, pr_body: str, diff: str) -> str:
    """Generate comprehensive top-level PR review and summary."""
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
    return call_gemini_api(api_key, prompt)


def generate_comment_reply(
    api_key: str,
    pr_title: str,
    pr_body: str,
    diff: str,
    comment_author: str,
    comment_body: str,
) -> str:
    """Generate detailed plain-English response to an on-demand user comment."""
    cleaned_query = re.sub(
        r"^\s*(/\s*(gemini|ci\s*gemini|ci-gemini|review|explain)|@gemini)\s*",
        "",
        comment_body,
        flags=re.IGNORECASE,
    ).strip()

    is_general_review = (
        cleaned_query == ""
        or cleaned_query.lower()
        in [
            "review",
            "review code",
            "review the code",
            "review the whole code",
            "explain",
            "explain code",
            "explain the code",
            "summary",
            "detail summary",
            "give me a detail summary",
            "what does this pr do",
            "what does this pr do?",
        ]
        or cleaned_query.lower().startswith("review")
    )

    if is_general_review:
        instructions = f"""The user @{comment_author} requested a complete, in-depth, plain-English explanation of everything this Pull Request does and what it fixed.

Structure your response clearly with these sections:
1. Overview in Plain English: Explain what this PR does so that anyone can understand it without complex jargon.
2. What Was Broken / What Was Missing: Explain the exact problem that existed before this change.
3. How the Fix / Feature Works: Walk through the algorithmic, mathematical, or architectural approach step-by-step.
4. Key File Changes: Detail what each modified file does and why it was changed.
5. Performance & Quality Impact: Summarize benchmark results (TEDS, CER, WER), test validation, and memory efficiency (<250MB RSS).
6. Summary & Takeaway: A brief wrap-up of why this change improves the parser.
"""
    else:
        instructions = f"""The user @{comment_author} asked a specific question or requested specific details:
"{cleaned_query}"

Provide a thorough, direct, and crystal-clear response answering their question in simple, easy-to-understand terms while preserving deep technical accuracy. Refer directly to the code changes and diff where helpful."""

    prompt = f"""You are Gemini Code Intelligence for universal-doc-parser.
A developer or user has commented on Pull Request: "{pr_title}".

User: @{comment_author}
User Comment:
{comment_body}

PR Description:
{pr_body or "No description provided."}

PR Git Diff:
{diff}

Task:
{instructions}

Format Guidelines:
- Header: `### Response for @{comment_author} by Gemini Code Intelligence`
- Write in clear, structured GitHub Markdown with bullet points, code blocks, or tables as helpful.
- Explain technical concepts in plain, accessible language so anyone can track what the PR is doing.
- Do not use emojis anywhere in the output.
- Wrap all file names, functions, classes, and variables in backticks.
"""
    return call_gemini_api(api_key, prompt)


def post_top_summary_comment(
    github_token: str,
    repo: str,
    pr_number: int,
    comment_body: str,
) -> None:
    """Post or update the top-level pinned review comment on the PR."""
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
                body = c.get("body", "")
                if (
                    "### PR Detailed Review & Summary by Gemini" in body
                    or "### PR Summary by Gemini" in body
                ):
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
        print(f"Successfully posted/updated top PR summary comment (status: {resp.status})")


def post_reply_comment(
    github_token: str,
    repo: str,
    pr_number: int,
    comment_body: str,
) -> None:
    """Always post a new comment in response to a user comment on the PR."""
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "universal-doc-parser-ci",
    }
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    payload = json.dumps({"body": comment_body}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

    with urllib.request.urlopen(req, timeout=15) as resp:
        print(f"Successfully posted reply comment to PR #{pr_number} (status: {resp.status})")


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

    is_comment_event = False
    comment_author = ""
    comment_body = ""

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
        is_comment_event = True
        pr_number = event_data["issue"]["number"]
        pr_title = event_data["issue"].get("title", "")
        pr_body = event_data["issue"].get("body", "")
        if "comment" in event_data:
            comment_author = event_data["comment"].get("user", {}).get("login", "user")
            comment_body = event_data["comment"].get("body", "")

        try:
            pr_api_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
            req_pr = urllib.request.Request(pr_api_url, headers=headers, method="GET")
            with urllib.request.urlopen(req_pr, timeout=15) as resp:
                pr_info = json.loads(resp.read().decode("utf-8"))
                base_branch = pr_info.get("base", {}).get("ref", "main")
                head_ref = pr_info.get("head", {}).get("ref")
                if not pr_title:
                    pr_title = pr_info.get("title", "")
                if not pr_body:
                    pr_body = pr_info.get("body", "")
        except Exception as e:
            print(f"Could not fetch PR info from API: {e}")

    if not pr_number:
        print("Event is not associated with a Pull Request. Exiting.")
        sys.exit(0)

    print(
        f"Processing PR #{pr_number}: {pr_title} (is_comment={is_comment_event}, base={base_branch}, head={head_ref})..."
    )
    diff = get_pr_diff(repo, pr_number, github_token, base_branch, head_ref)
    if not diff:
        print("No git diff detected for this PR. Skipping review.")
        sys.exit(0)

    try:
        if is_comment_event:
            print(f"Generating on-demand reply for @{comment_author}...")
            reply = generate_comment_reply(
                api_key,
                pr_title,
                pr_body,
                diff,
                comment_author,
                comment_body,
            )
            post_reply_comment(github_token, repo, pr_number, reply)
        else:
            print("Generating top PR summary...")
            summary = generate_pr_top_summary(api_key, pr_title, pr_body, diff)
            post_top_summary_comment(github_token, repo, pr_number, summary)
    except Exception as e:
        print(f"Error during Gemini PR review execution: {e}")
        sys.exit(0)


if __name__ == "__main__":
    main()
