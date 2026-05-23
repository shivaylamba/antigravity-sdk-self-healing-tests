# Test Runner Templates

Use `--test-runner` and `--test-command` for your stack:

- Python / pytest: `--test-runner pytest --test-command "pytest"`
- JavaScript / jest: `--test-runner jest --test-command "npm test"`
- JavaScript / playwright: `--test-runner playwright --test-command "npx playwright test"`
- Java / maven surefire: `--test-runner maven-surefire --test-command "mvn test"`
- Go: `--test-runner go-test --test-command "go test ./..."`
