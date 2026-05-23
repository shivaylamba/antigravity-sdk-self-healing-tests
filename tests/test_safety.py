from src.safety import GuardrailResult
from src.safety import enforce_guardrails
from src.types import SafetyControls


def test_guardrail_result_defaults():
    result = GuardrailResult(ok=True)
    assert result.ok is True
    assert result.patch_lines == 0


def test_enforce_guardrails_patch_size(monkeypatch, tmp_path):
    monkeypatch.setattr("src.safety.capture_git_changes", lambda cwd: (["src/a.py"], 20))
    controls = SafetyControls(maxPatchLines=10, allowedPaths=[])
    result = enforce_guardrails(str(tmp_path), controls)
    assert result.ok is False
    assert "Patch too large" in result.reason
    assert result.changed_files == ["src/a.py"]
    assert result.patch_lines == 20


def test_enforce_guardrails_allowed_paths(monkeypatch, tmp_path):
    monkeypatch.setattr("src.safety.capture_git_changes", lambda cwd: (["docs/readme.md"], 2))
    controls = SafetyControls(maxPatchLines=100, allowedPaths=["src", "tests"])
    result = enforce_guardrails(str(tmp_path), controls)
    assert result.ok is False
    assert "outside allowed paths" in result.reason
    assert result.changed_files == ["docs/readme.md"]
    assert result.patch_lines == 2
