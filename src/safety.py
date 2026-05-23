import os
import subprocess
from dataclasses import dataclass, field
from typing import List, Tuple
import shutil

from .types import SafetyControls


@dataclass
class GuardrailResult:
    ok: bool
    reason: str = ""
    changed_files: List[str] = field(default_factory=list)
    patch_lines: int = 0


def capture_git_changes(cwd: str) -> Tuple[List[str], int]:
    files: List[str] = []
    patch_lines = 0
    try:
        status = subprocess.run(
            ["git", "--no-pager", "status", "--porcelain"],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        ).stdout
        for line in status.splitlines():
            if len(line) > 3:
                files.append(line[3:].strip())
        diff = subprocess.run(
            ["git", "--no-pager", "diff", "--numstat"],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        ).stdout
        for row in diff.splitlines():
            cols = row.split("\t")
            if len(cols) >= 2 and cols[0].isdigit() and cols[1].isdigit():
                patch_lines += int(cols[0]) + int(cols[1])
    except Exception:
        return ([], 0)
    return (files, patch_lines)


def enforce_guardrails(cwd: str, controls: SafetyControls) -> GuardrailResult:
    changed_files, patch_lines = capture_git_changes(cwd)
    allowed_paths = controls.allowed_paths or []

    if allowed_paths:
        for changed in changed_files:
            if not any(_is_allowed_path(changed, ap) for ap in allowed_paths):
                return GuardrailResult(
                    ok=False,
                    reason=f"File outside allowed paths was modified: {changed}",
                    changed_files=changed_files,
                    patch_lines=patch_lines,
                )

    if patch_lines > controls.max_patch_lines:
        return GuardrailResult(
            ok=False,
            reason=f"Patch too large: {patch_lines} lines changed (max {controls.max_patch_lines})",
            changed_files=changed_files,
            patch_lines=patch_lines,
        )

    return GuardrailResult(ok=True, changed_files=changed_files, patch_lines=patch_lines)


def rollback_changes(cwd: str, changed_files: List[str]) -> None:
    for path in changed_files or []:
        full_path = os.path.join(cwd, path)
        if _is_git_tracked(cwd, path):
            subprocess.run(["git", "--no-pager", "checkout", "--", path], cwd=cwd, check=False)
            continue
        if os.path.isdir(full_path):
            shutil.rmtree(full_path, ignore_errors=True)
        elif os.path.isfile(full_path):
            try:
                os.remove(full_path)
            except FileNotFoundError:
                pass


def _is_allowed_path(changed: str, allowed: str) -> bool:
    normalized_changed = os.path.normpath(changed)
    normalized_allowed = os.path.normpath(allowed.rstrip("/"))
    if normalized_changed == normalized_allowed:
        return True
    return normalized_changed.startswith(normalized_allowed + os.sep)


def _is_git_tracked(cwd: str, path: str) -> bool:
    res = subprocess.run(
        ["git", "--no-pager", "ls-files", "--error-unmatch", path],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    return res.returncode == 0
