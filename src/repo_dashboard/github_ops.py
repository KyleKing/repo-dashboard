import asyncio
import json
import subprocess
from pathlib import Path

from repo_dashboard.models import PRDetail, PRInfo
from repo_dashboard.vcs_factory import get_github_env, get_vcs_operations


def _get_checks_status(rollup: list | None) -> str | None:
    if not rollup:
        return None

    states = [check.get("conclusion") or check.get("state", "") for check in rollup]
    if not states:
        return None

    if all(s in ("SUCCESS", "COMPLETED") for s in states):
        return "passing"
    if any(s in ("FAILURE", "ERROR") for s in states):
        return "failing"
    if any(s in ("PENDING", "IN_PROGRESS", "QUEUED") for s in states):
        return "pending"
    return "unknown"


def _parse_pr_response(stdout: str) -> PRInfo | None:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return None

    checks_status = _get_checks_status(data.get("statusCheckRollup"))

    return PRInfo(
        number=data["number"],
        title=data["title"],
        url=data["url"],
        state=data["state"],
        checks_status=checks_status,
    )


def get_pr_for_branch(path: Path, branch: str) -> PRInfo | None:
    vcs_ops = get_vcs_operations(path)
    env = get_github_env(vcs_ops, path)

    result = subprocess.run(
        [
            "gh",
            "pr",
            "view",
            branch,
            "--json",
            "number,title,url,state,statusCheckRollup",
        ],
        cwd=path,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None

    return _parse_pr_response(result.stdout)


async def get_pr_for_branch_async(path: Path, branch: str) -> PRInfo | None:
    vcs_ops = get_vcs_operations(path)
    env = get_github_env(vcs_ops, path)

    proc = await asyncio.create_subprocess_exec(
        "gh",
        "pr",
        "view",
        branch,
        "--json",
        "number,title,url,state,statusCheckRollup",
        cwd=path,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()

    if proc.returncode != 0:
        return None

    return _parse_pr_response(stdout.decode())


async def get_pr_detail(path: Path, branch: str) -> PRDetail | None:
    """Get extended PR details including description and comments"""
    vcs_ops = get_vcs_operations(path)
    env = get_github_env(vcs_ops, path)

    proc = await asyncio.create_subprocess_exec(
        "gh",
        "pr",
        "view",
        branch,
        "--json",
        "number,title,url,state,statusCheckRollup,body,comments,additions,deletions",
        cwd=path,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()

    if proc.returncode != 0:
        return None

    try:
        data = json.loads(stdout.decode())
    except json.JSONDecodeError:
        return None

    unresolved = sum(
        1 for c in data.get("comments", [])
        if not c.get("isResolved", True)
    )

    return PRDetail(
        number=data["number"],
        title=data["title"],
        url=data["url"],
        state=data["state"],
        checks_status=_get_checks_status(data.get("statusCheckRollup")),
        description=data.get("body", ""),
        unresolved_comments=unresolved,
        additions=data.get("additions", 0),
        deletions=data.get("deletions", 0),
    )
