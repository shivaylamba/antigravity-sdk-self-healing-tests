import json
import os
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ValidationError

from .types import SafetyControls


DEFAULT_CONFIG_PATH = ".antigravity-healer/config.json"


class AppConfig(BaseModel):
    provider: Optional[str] = None
    test_runner: Optional[str] = Field(default=None, alias="testRunner")
    vcs: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = Field(default=None, alias="apiKey")
    test_command: Optional[str] = Field(default=None, alias="testCommand")
    mode: Optional[str] = None
    safety: SafetyControls = Field(default_factory=SafetyControls)


def _read_json(path: str) -> Dict[str, Any]:
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _env_config() -> Dict[str, Any]:
    return {
        "provider": os.environ.get("AG_PROVIDER"),
        "testRunner": os.environ.get("AG_TEST_RUNNER"),
        "vcs": os.environ.get("AG_VCS"),
        "model": os.environ.get("GEMINI_MODEL"),
        "apiKey": os.environ.get("GEMINI_API_KEY") or os.environ.get("CURSOR_API_KEY"),
        "testCommand": os.environ.get("TEST_COMMAND"),
        "mode": os.environ.get("AG_MODE"),
        "safety": {
            "maxHealingAttempts": os.environ.get("AG_MAX_HEALING_ATTEMPTS"),
            "allowedPaths": [p.strip() for p in os.environ.get("AG_ALLOWED_PATHS", "").split(",") if p.strip()],
            "maxPatchLines": os.environ.get("AG_MAX_PATCH_LINES"),
            "rollbackOnGuardrailViolation": os.environ.get("AG_ROLLBACK_ON_GUARDRAIL_VIOLATION"),
            "auditLogPath": os.environ.get("AG_AUDIT_LOG_PATH"),
        },
    }


def _normalize_values(config: Dict[str, Any]) -> Dict[str, Any]:
    result = {}
    for k, v in config.items():
        if isinstance(v, dict):
            nested = _normalize_values(v)
            if nested:
                result[k] = nested
        elif v is not None and v != "":
            result[k] = v

    safety = result.get("safety")
    if isinstance(safety, dict):
        if "maxHealingAttempts" in safety:
            safety["maxHealingAttempts"] = int(safety["maxHealingAttempts"])
        if "maxPatchLines" in safety:
            safety["maxPatchLines"] = int(safety["maxPatchLines"])
        if "rollbackOnGuardrailViolation" in safety:
            value = str(safety["rollbackOnGuardrailViolation"]).lower()
            safety["rollbackOnGuardrailViolation"] = value in ("1", "true", "yes", "on")
    return result


def merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = merge_configs(merged[k], v)
        else:
            merged[k] = v
    return merged


def load_app_config(cwd: str, config_path: Optional[str], cli_overrides: Dict[str, Any]) -> AppConfig:
    effective_path = config_path or DEFAULT_CONFIG_PATH
    if not os.path.isabs(effective_path):
        effective_path = os.path.join(cwd, effective_path)

    file_data = _normalize_values(_read_json(effective_path))
    env_data = _normalize_values(_env_config())
    cli_data = _normalize_values(cli_overrides)

    merged = merge_configs(file_data, env_data)
    merged = merge_configs(merged, cli_data)
    try:
        return AppConfig.model_validate(merged)
    except ValidationError as e:
        raise ValueError(f"Invalid configuration: {e}") from e
