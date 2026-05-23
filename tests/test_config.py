from src.config import load_app_config


def test_config_precedence_cli_over_env_over_file(tmp_path, monkeypatch):
    cfg = tmp_path / "config.json"
    cfg.write_text(
        '{"provider":"manual","testRunner":"pytest","testCommand":"pytest -q","safety":{"maxPatchLines":100}}',
        encoding="utf-8",
    )
    monkeypatch.setenv("AG_PROVIDER", "gitlab-ci")
    monkeypatch.setenv("TEST_COMMAND", "pytest tests")

    config = load_app_config(
        cwd=str(tmp_path),
        config_path=str(cfg),
        cli_overrides={"provider": "github-actions", "safety": {"maxPatchLines": 25}},
    )

    assert config.provider == "github-actions"
    assert config.test_command == "pytest tests"
    assert config.safety.max_patch_lines == 25
