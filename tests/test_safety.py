from src.safety import GuardrailResult


def test_guardrail_result_defaults():
    result = GuardrailResult(ok=True)
    assert result.ok is True
    assert result.patch_lines == 0
