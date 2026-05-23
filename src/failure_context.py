import os
import re
import subprocess
from typing import List, Optional, Dict, Any
from .types import FailureContext
from .adapters.tests import auto_detect_test_adapter
from .fs_utils import read_json_if_exists, read_text_if_exists, resolve_from, write_json

MAX_LOG_CHARS = 12000
ENV_ALLOWED_PREFIXES = ("GITHUB_", "CI_", "CIRCLE_", "JENKINS_", "BUILD_", "GIT_")
ENV_REDACTION_MARKERS = ("TOKEN", "KEY", "SECRET", "PASSWORD")

async def build_failure_context(
    cwd: str,
    failure_file: Optional[str] = None,
    log_file: Optional[str] = None,
    report_paths: Optional[List[str]] = None,
    test_command: Optional[str] = None,
    provider: Optional[str] = None,
) -> FailureContext:
    if report_paths is None:
        report_paths = []

    loaded: Optional[Dict[str, Any]] = None
    if failure_file:
        loaded = read_json_if_exists(resolve_from(cwd, failure_file)) or {}
    else:
        loaded = {}

    log_excerpt = await read_log_excerpt(cwd, log_file)
    git_context = await read_git_context(cwd)
    github_env = read_github_environment()

    provider_value = loaded.get("provider") or provider or ("github-actions" if os.environ.get("GITHUB_ACTIONS") else "manual")
    detected_adapter = auto_detect_test_adapter(test_command)
    failed_tests = loaded.get("failedTests") or detected_adapter.infer_failed_tests(log_excerpt)

    # Merge contexts
    context_data = {
        "provider": provider_value,
        "pipelineId": loaded.get("pipelineId") or github_env.get("runId"),
        "pipelineUrl": loaded.get("pipelineUrl") or github_env.get("runUrl"),
        "pipelineName": loaded.get("pipelineName") or os.environ.get("GITHUB_WORKFLOW"),
        "repository": loaded.get("repository") or github_env.get("repository"),
        "repoUrl": loaded.get("repoUrl") or github_env.get("repoUrl") or git_context.get("remoteUrl"),
        "branch": loaded.get("branch") or github_env.get("branch") or git_context.get("branch"),
        "baseBranch": loaded.get("baseBranch") or github_env.get("baseBranch"),
        "commitSha": loaded.get("commitSha") or github_env.get("sha") or git_context.get("sha"),
        "runId": loaded.get("runId") or github_env.get("runId"),
        "runUrl": loaded.get("runUrl") or github_env.get("runUrl"),
        "jobName": loaded.get("jobName") or github_env.get("jobName"),
        "failedTests": failed_tests,
        "testCommand": loaded.get("testCommand") or test_command,
        "reportPaths": list(set(loaded.get("reportPaths", []) + report_paths)),
        "artifacts": loaded.get("artifacts", []),
        "environment": loaded.get("environment") or _safe_environment_subset(),
        "logExcerpt": loaded.get("logExcerpt") or log_excerpt,
        "rawEventPath": loaded.get("rawEventPath") or os.environ.get("GITHUB_EVENT_PATH"),
    }

    # Validate/Convert into FailureContext model
    context = FailureContext.model_validate(context_data)

    # Write to target
    write_json(os.path.join(cwd, ".antigravity-healer", "failure-context.json"), context.model_dump(by_alias=True))
    return context

async def read_log_excerpt(cwd: str, log_file: Optional[str]) -> Optional[str]:
    if not log_file:
        return None
    full_path = resolve_from(cwd, log_file)
    text = read_text_if_exists(full_path)
    if not text:
        return None
    if len(text) > MAX_LOG_CHARS:
        return text[-MAX_LOG_CHARS:]
    return text

def infer_failed_tests(log_excerpt: Optional[str]) -> List[str]:
    if not log_excerpt:
        return []
    
    names = set()
    patterns = [
        r"^\s*(?:FAIL|FAILED)\s+(.+)$",
        r"^\s*✘\s+\d*\s*(.+)$",
        r"^\s*×\s+(.+)$",
        r"^\s*not ok\s+\d*\s*(.+)$"
    ]
    
    for line in log_excerpt.splitlines():
        for pat in patterns:
            match = re.match(pat, line, re.IGNORECASE)
            if match:
                names.add(match.group(1).strip())
                
    return list(names)[:20]

async def read_git_context(cwd: str) -> Dict[str, Optional[str]]:
    def run_git(args: List[str]) -> Optional[str]:
        try:
            res = subprocess.run(
                ["git"] + args,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            return res.stdout.strip() or None
        except Exception:
            return None

    return {
        "branch": run_git(["rev-parse", "--abbrev-ref", "HEAD"]),
        "sha": run_git(["rev-parse", "HEAD"]),
        "remoteUrl": run_git(["config", "--get", "remote.origin.url"]),
    }

def read_github_environment() -> Dict[str, Optional[str]]:
    repository = os.environ.get("GITHUB_REPOSITORY")
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    run_id = os.environ.get("GITHUB_RUN_ID")

    return {
        "repository": repository,
        "repoUrl": f"{server_url}/{repository}" if repository else None,
        "branch": os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GITHUB_REF_NAME"),
        "baseBranch": os.environ.get("GITHUB_BASE_REF"),
        "sha": os.environ.get("GITHUB_SHA"),
        "runId": run_id,
        "runUrl": f"{server_url}/{repository}/actions/runs/{run_id}" if repository and run_id else None,
        "jobName": os.environ.get("GITHUB_JOB"),
    }


def _safe_environment_subset() -> Dict[str, str]:
    result: Dict[str, str] = {}
    for k, v in os.environ.items():
        if not k.startswith(ENV_ALLOWED_PREFIXES):
            continue
        key_parts = k.split("_")
        if any(marker in key_parts or k.endswith(marker) for marker in ENV_REDACTION_MARKERS):
            result[k] = "***REDACTED***"
        else:
            result[k] = v
    return result
