import asyncio
import json
import subprocess
from pathlib import Path

from repo_dashboard.models import PRDetail, PRInfo, WorkflowRun, WorkflowSummary
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


async def get_workflow_runs_for_commit(path: Path, commit_sha: str) -> WorkflowSummary | None:
    """Get workflow runs for a specific commit SHA"""
    from datetime import datetime

    vcs_ops = get_vcs_operations(path)
    env = get_github_env(vcs_ops, path)

    proc = await asyncio.create_subprocess_exec(
        "gh",
        "run",
        "list",
        "--commit",
        commit_sha,
        "--json",
        "status,conclusion,headSha,name,workflowName,databaseId,createdAt,url",
        "--limit",
        "100",
        cwd=path,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()

    if proc.returncode != 0:
        return None

    try:
        runs_data = json.loads(stdout.decode())
    except json.JSONDecodeError:
        return None

    if not runs_data:
        return None

    workflow_runs = []
    success_count = 0
    failure_count = 0
    skipped_count = 0
    pending_count = 0

    for run in runs_data:
        status = run.get("status", "").lower()
        conclusion = run.get("conclusion", "").lower() if run.get("conclusion") else None

        try:
            created_at = datetime.fromisoformat(run["createdAt"].replace("Z", "+00:00"))
        except (ValueError, KeyError):
            created_at = datetime.now()

        workflow_run = WorkflowRun(
            workflow_name=run.get("workflowName") or run.get("name", "Unknown"),
            run_id=run.get("databaseId", 0),
            status=status,
            conclusion=conclusion,
            created_at=created_at,
            html_url=run.get("url", ""),
        )
        workflow_runs.append(workflow_run)

        if status == "completed":
            if conclusion == "success":
                success_count += 1
            elif conclusion in ("failure", "timed_out", "action_required"):
                failure_count += 1
            elif conclusion == "skipped":
                skipped_count += 1
        else:
            pending_count += 1

    return WorkflowSummary(
        success_count=success_count,
        failure_count=failure_count,
        skipped_count=skipped_count,
        pending_count=pending_count,
        runs=workflow_runs,
    )


async def get_workflow_runs_for_branch(path: Path, branch: str) -> WorkflowSummary | None:
    """Get workflow runs for the latest commit on a branch"""
    vcs_ops = get_vcs_operations(path)

    commit_sha = await vcs_ops.get_commit_sha(path, branch)
    if not commit_sha:
        return None

    return await get_workflow_runs_for_commit(path, commit_sha)

