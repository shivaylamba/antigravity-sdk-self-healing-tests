# Antigravity Self-Healing Tests

Repair failing test runs autonomously using the **Google Antigravity Python SDK**. This project is a Python-based replication of the Cursor-SDK self-healing test workflow.

When your CI/CD tests fail, the Antigravity Agent:
1. Inspects the workspace, test log files, and report paths.
2. Formulates the likely root cause.
3. Automatically applies the minimum necessary code or test fixes.
4. Executes the verification command locally to confirm it passes.
5. Emits the summary of changes and results.

---

## Installation

Ensure you have Python 3.10+ installed.

```bash
pip install -r requirements.txt
```

---

## Local Usage

Run tests and capture the logs:
```bash
pytest > .antigravity-test.log 2>&1
```

If it fails, invoke the healer agent:
```bash
python -m src.cli heal \
  --log-file .antigravity-test.log \
  --test-command "pytest" \
  --api-key "YOUR_GEMINI_API_KEY"
```

### CLI Options

- `heal`:
  - `--log-file`: Path to the test output logs (default: `.antigravity-test.log`).
  - `--report`: Comma-separated list of paths to check (default: `test-results,playwright-report,coverage`).
  - `--test-command`: Verification command to execute after changes (default: value of `$TEST_COMMAND` or `npm test`).
  - `--dry-run`: Evaluate and report the failure without performing file edits.
  - `--model`: Gemini model (default: `$GEMINI_MODEL` or `gemini-3.5-flash`).
  - `--api-key`: Gemini API Key (default: `$GEMINI_API_KEY` or `$CURSOR_API_KEY`).
  - `--failure-file`: Override failure JSON path.
- `server`:
  - `--port`: Webhook port to listen on (default: `8787` or `$PORT`).
  - `--model`: Gemini model.
  - `--api-key`: Gemini API key.
  - `--webhook-secret`: Optional webhook signature secret.

---

## GitHub Actions Workflow Integration

Include the action in your repository workflow to automatically submit PRs with fixes:

```yaml
name: Self-healing tests

on:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run tests
        id: tests
        continue-on-error: true
        run: |
          pytest 2>&1 | tee .antigravity-test.log

      - name: Ask Antigravity to repair
        if: steps.tests.outcome == 'failure'
        uses: shivaylamba/antigravity-self-healing-tests@v1
        with:
          gemini-api-key: ${{ secrets.GEMINI_API_KEY }}
          model: gemini-3.5-flash
          log-file: .antigravity-test.log
          test-command: pytest

      - name: Detect changes
        if: steps.tests.outcome == 'failure'
        id: changes
        run: |
          if [ -n "$(git status --porcelain)" ]; then
            echo "changed=true" >> "$GITHUB_OUTPUT"
          else
            echo "changed=false" >> "$GITHUB_OUTPUT"
          fi

      - name: Create repair pull request
        if: steps.tests.outcome == 'failure' && steps.changes.outputs.changed == 'true'
        uses: peter-evans/create-pull-request@v6
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          branch: antigravity/self-heal-${{ github.run_id }}
          title: "test: self-heal failing tests"
          body-path: .antigravity-healer/result.md
          add-paths: |
            .
            :!.antigravity-healer/**
            :!.antigravity-test.log
