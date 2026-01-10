import json
import subprocess
from pathlib import Path

from multi_repo_view.models import PRInfo


def get_pr_for_branch(path: Path, branch: str) -> PRInfo | None:
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
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None

    try:
        data = json.loads(result.stdout)
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
