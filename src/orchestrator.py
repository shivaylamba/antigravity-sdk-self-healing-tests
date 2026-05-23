import json
import os
import shlex
import subprocess
from datetime import datetime, timezone
from typing import Optional

from .adapters import auto_detect_provider, auto_detect_test_adapter
from .agent_runner import run_healing_agent
from .adapters.providers import CircleCIAdapter, GitHubActionsAdapter, GitLabCIAdapter, JenkinsAdapter, ManualAdapter
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
            passed, verify_stdout, verify_stderr = _run_verify(options.cwd, options.test_command)
            _audit(
                options.cwd,
                options.safety.audit_log_path,
                {
                    "phase": "verify",
                    "attempt": attempt,
                    "passed": passed,
                    "command": options.test_command,
                    "stdoutTail": verify_stdout[-2000:] if verify_stdout else "",
                    "stderrTail": verify_stderr[-2000:] if verify_stderr else "",
                },
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
        provider_map = {
            "github-actions": GitHubActionsAdapter,
            "gitlab-ci": GitLabCIAdapter,
            "jenkins": JenkinsAdapter,
            "circleci": CircleCIAdapter,
            "manual": ManualAdapter,
        }
        provider_cls = provider_map.get(provider_name)
        if provider_cls:
            provider = provider_cls()

    context = provider.build_context(cwd, dict(os.environ), log_excerpt)
    context.test_command = test_command

    test_adapter = auto_detect_test_adapter(test_command)
    context.failed_tests = test_adapter.infer_failed_tests(log_excerpt)
    context.report_paths = list(dict.fromkeys(context.report_paths))
    return context


def _ensure_output_dir(cwd: str) -> None:
    os.makedirs(os.path.join(cwd, ".antigravity-healer"), exist_ok=True)


def _run_verify(cwd: str, command: str) -> tuple[bool, str, str]:
    res = subprocess.run(
        shlex.split(command),
        cwd=cwd,
        shell=False,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return (res.returncode == 0, res.stdout or "", res.stderr or "")


def _audit(cwd: str, audit_log_path: str, payload: dict) -> None:
    path = audit_log_path if os.path.isabs(audit_log_path) else os.path.join(cwd, audit_log_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    line = {
        "time": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")
