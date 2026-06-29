"""
Publish an audit report HTML file to GitHub Pages.

Each location gets one repo: nexudus-audit-{business-id}
Pages URL: https://{gh-user}.github.io/nexudus-audit-{business-id}/

The HTML is pushed as index.html via the GitHub Contents API (no git clone
needed). On first publish the repo is created and Pages is enabled.
Subsequent publishes just update index.html in place.
"""

import base64
import json
import subprocess
import sys


def _gh(args: list, input_data: str = None) -> dict:
    cmd = ["gh", "api"] + args
    if input_data is not None:
        cmd += ["--input", "-"]
    result = subprocess.run(
        cmd,
        input=input_data,
        capture_output=True,
        text=True,
    )
    try:
        return {"ok": result.returncode == 0, "data": json.loads(result.stdout), "stderr": result.stderr}
    except json.JSONDecodeError:
        return {"ok": result.returncode == 0, "data": {}, "stderr": result.stderr, "stdout": result.stdout}


def _gh_user() -> str:
    result = subprocess.run(["gh", "api", "user", "--jq", ".login"], capture_output=True, text=True)
    return result.stdout.strip()


def _repo_exists(owner: str, repo: str) -> bool:
    r = _gh([f"/repos/{owner}/{repo}"])
    return r["ok"]


def _create_repo(owner: str, repo: str, description: str):
    _gh(
        ["--method", "POST", "/user/repos"],
        input_data=json.dumps({
            "name": repo,
            "description": description,
            "private": False,
            "auto_init": True,
        }),
    )


def _get_file_sha(owner: str, repo: str, path: str) -> str | None:
    r = _gh([f"/repos/{owner}/{repo}/contents/{path}"])
    if r["ok"] and isinstance(r["data"], dict):
        return r["data"].get("sha")
    return None


def _put_file(owner: str, repo: str, path: str, content_b64: str, message: str, sha: str = None):
    body = {"message": message, "content": content_b64}
    if sha:
        body["sha"] = sha
    _gh(
        ["--method", "PUT", f"/repos/{owner}/{repo}/contents/{path}"],
        input_data=json.dumps(body),
    )


def _enable_pages(owner: str, repo: str):
    _gh(
        ["--method", "POST", f"/repos/{owner}/{repo}/pages"],
        input_data=json.dumps({"build_type": "legacy", "source": {"branch": "main", "path": "/"}}),
    )


def publish(html_path: str, business_id: str, business_name: str, run_date) -> str:
    owner = _gh_user()
    repo  = f"nexudus-audit-{business_id}"
    url   = f"https://{owner}.github.io/{repo}/"

    is_new = not _repo_exists(owner, repo)

    if is_new:
        _create_repo(owner, repo, f"AI Agent Audit — {business_name}")
        # Brief pause for GitHub to initialise the repo before we push
        import time; time.sleep(3)

    with open(html_path, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode()

    # Push as index.html (the live report)
    sha = _get_file_sha(owner, repo, "index.html")
    _put_file(
        owner, repo, "index.html", content_b64,
        message=f"Audit report — {run_date.isoformat()}",
        sha=sha,
    )

    # Also archive a dated copy so history is preserved
    dated_path = f"reports/{run_date.isoformat()}.html"
    dated_sha  = _get_file_sha(owner, repo, dated_path)
    _put_file(
        owner, repo, dated_path, content_b64,
        message=f"Archive — {run_date.isoformat()}",
        sha=dated_sha,
    )

    if is_new:
        _enable_pages(owner, repo)

    return url
