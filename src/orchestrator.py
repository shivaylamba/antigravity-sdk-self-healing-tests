import json
import os
import subprocess
from datetime import datetime, timezone
from typing import Optional

from .adapters import auto_detect_provider, auto_detect_test_adapter
from .agent_runner import run_healing_agent
from .failure_context import read_log_excerpt
from .safety import enforce_guardrails, rollback_changes
from .types import FailureContext, HealOptions, HealResult


async def run_healing_loop(options: HealOptions) -> HealResult:
    _ensure_output_dir(options.cwd)
    _audit(options.cwd, options.safety.audit_log_path, {"phase": "start", "mode": options.mode})

    for attempt in range(1, options.safety.max_healing_attempts + 1):
        _audit(options.cwd, options.safety.audit_log_path, {"phase": "attempt_start", "attempt": attempt})
        result = await run_healing_agent(options)

        guardrails = enforce_guardrails(options.cwd, options.safety)
        _audit(
            options.cwd,
            options.safety.audit_log_path,
            {
                "phase": "guardrails",
                "attempt": attempt,
                "ok": guardrails.ok,
                "patchLines": guardrails.patch_lines,
                "changedFiles": guardrails.changed_files,
                "reason": guardrails.reason,
            },
        )

        if not guardrails.ok and options.safety.rollback_on_guardrail_violation:
            rollback_changes(options.cwd, guardrails.changed_files or [])
            result.status = "error"
            result.result = f"Guardrail violation: {guardrails.reason}"
            return result

        if options.test_command:
            passed = _run_verify(options.cwd, options.test_command)
            _audit(
                options.cwd,
                options.safety.audit_log_path,
                {"phase": "verify", "attempt": attempt, "passed": passed, "command": options.test_command},
            )
            if passed:
                return result
        else:
            return result
    result.status = "error"
    result.result = "Maximum healing attempts exhausted."
    return result


async def build_context_with_adapters(
    cwd: str,
    provider_name: Optional[str],
    test_command: Optional[str],
    log_file: Optional[str],
) -> FailureContext:
    log_excerpt = await read_log_excerpt(cwd, log_file)
    provider = auto_detect_provider(dict(os.environ))
    if provider_name:
        # name override only when matching built-in names
        for candidate in ("github-actions", "gitlab-ci", "jenkins", "circleci", "manual"):
            if provider_name == candidate:
                if candidate == "manual":
                    from .adapters.providers import ManualAdapter

                    provider = ManualAdapter()
                elif candidate == "github-actions":
                    from .adapters.providers import GitHubActionsAdapter

                    provider = GitHubActionsAdapter()
                elif candidate == "gitlab-ci":
                    from .adapters.providers import GitLabCIAdapter

                    provider = GitLabCIAdapter()
                elif candidate == "jenkins":
                    from .adapters.providers import JenkinsAdapter

                    provider = JenkinsAdapter()
                elif candidate == "circleci":
                    from .adapters.providers import CircleCIAdapter

                    provider = CircleCIAdapter()

    context = provider.build_context(cwd, dict(os.environ), log_excerpt)
    context.test_command = test_command

    test_adapter = auto_detect_test_adapter(test_command)
    context.failed_tests = test_adapter.infer_failed_tests(log_excerpt)
    context.report_paths = list(dict.fromkeys(context.report_paths))
    return context


def _ensure_output_dir(cwd: str) -> None:
    os.makedirs(os.path.join(cwd, ".antigravity-healer"), exist_ok=True)


def _run_verify(cwd: str, command: str) -> bool:
    res = subprocess.run(command, cwd=cwd, shell=True, check=False)
    return res.returncode == 0


def _audit(cwd: str, audit_log_path: str, payload: dict) -> None:
    path = audit_log_path if os.path.isabs(audit_log_path) else os.path.join(cwd, audit_log_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    line = {
        "time": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")
