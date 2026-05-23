# Antigravity Self-Healing Engine (CI-Agnostic)

This project implements a **CI/CD-agnostic self-healing agent loop** powered by the Google Antigravity SDK.

It supports:
- Multiple CI providers (GitHub Actions, GitLab CI, Jenkins, CircleCI, manual/local)
- Multiple test runner styles (pytest, jest, playwright, maven/junit, go test, generic)
- Config layers (config file → environment variables → CLI overrides)
- Execution modes (local dry-run, local apply, CI autonomous, webhook server)
- Safety guardrails (attempt limits, allowed path constraints, patch-size limits, rollback, audit log)

---

## Architecture

Core flow:
1. **Detect** CI/runtime context through provider adapters
2. **Analyze** logs and failure context
3. **Patch** via Antigravity agent
4. **Verify** with configured test command
5. **Report** outputs and audit entries

Key modules:
- `src/orchestrator.py`: end-to-end healing loop
- `src/adapters/providers.py`: CI provider adapters
- `src/adapters/tests.py`: test runner adapters
- `src/adapters/vcs.py`: VCS integration abstraction
- `src/config.py`: merged config loading/validation
- `src/safety.py`: guardrails, rollback, change checks

---

## Installation

```bash
pip install -r requirements.txt
pip install pytest
```

---

## Quickstart

### Local dry-run
```bash
python -m src.cli heal \
  --mode local-dry-run \
  --log-file .antigravity-test.log \
  --test-command "pytest" \
  --api-key "$GEMINI_API_KEY"
```

### Local apply
```bash
python -m src.cli heal \
  --mode local-apply \
  --provider manual \
  --test-runner pytest \
  --log-file .antigravity-test.log \
  --test-command "pytest" \
  --api-key "$GEMINI_API_KEY"
```

> `--test-command` should be a direct command (for example `pytest` or `go test ./...`) and not a shell pipeline.

### CI autonomous
```bash
python -m src.cli heal \
  --mode ci-autonomous \
  --provider github-actions \
  --log-file .antigravity-test.log \
  --test-command "pytest" \
  --api-key "$GEMINI_API_KEY"
```

### Webhook server mode
```bash
python -m src.cli server --port 8787 --api-key "$GEMINI_API_KEY"
```

---

## Configuration

Default file: `.antigravity-healer/config.json`

Precedence (highest to lowest):
1. CLI flags
2. Environment variables
3. Config file

Example:
```json
{
  "provider": "github-actions",
  "testRunner": "pytest",
  "testCommand": "pytest",
  "mode": "ci-autonomous",
  "safety": {
    "maxHealingAttempts": 2,
    "allowedPaths": ["src", "tests"],
    "maxPatchLines": 250,
    "rollbackOnGuardrailViolation": true,
    "auditLogPath": ".antigravity-healer/audit.log"
  }
}
```

---

## Adapter Extension Guide

Add custom implementations for:
- `CIProviderAdapter` (`src/adapters/base.py`)
- `TestAdapter` (`src/adapters/base.py`)
- `VCSAdapter` (`src/adapters/base.py`)

Register them in `src/adapters/registry.py` (or call custom register functions at startup).

---

## CI & Test Templates

- CI templates: `examples/ci/`
  - GitHub Actions
  - GitLab CI
  - Jenkins
  - CircleCI
- Test runner templates: `examples/test-runners/README.md`

---

## Security & Operations

Guardrails include:
- Maximum healing attempts
- Allowed paths for changes
- Maximum patch size
- Rollback when guardrails fail
- Append-only audit log for every run

Recommended:
- Run with least-privilege tokens
- Keep `allowedPaths` narrowly scoped
- Use dry-run in production rollout phases first

---

## Release Plan

### MVP (current)
- Multi-provider CI adapter baseline
- Multi-runner failure inference baseline
- Config layering and safety controls
- CLI/server orchestration

### Next milestones
- Robust VCS PR/MR adapters (GitHub/GitLab APIs)
- Rich artifact/report collectors per provider
- Enterprise controls (policy packs, approvals, observability integrations)
