import re
from typing import List, Optional

from .base import TestAdapter
from .registry import register_test_adapter


class RegexTestAdapter:
    name = "generic"
    patterns = [
        r"^\s*(?:FAIL|FAILED)\s+(.+)$",
        r"^\s*✘\s+\d*\s*(.+)$",
        r"^\s*×\s+(.+)$",
        r"^\s*not ok\s+\d*\s*(.+)$",
    ]

    def can_handle_command(self, command: str) -> bool:
        return True

    def infer_failed_tests(self, log_excerpt: Optional[str]) -> List[str]:
        return _extract_with_patterns(log_excerpt, self.patterns)


class PytestAdapter(RegexTestAdapter):
    name = "pytest"
    patterns = [r"^\s*FAILED\s+(.+::.+)\s+-\s+.+$"]

    def can_handle_command(self, command: str) -> bool:
        return "pytest" in (command or "")


class JestAdapter(RegexTestAdapter):
    name = "jest"
    patterns = [r"^\s*●\s+(.+)$"]

    def can_handle_command(self, command: str) -> bool:
        cmd = command or ""
        return "jest" in cmd or "npm test" in cmd or "yarn test" in cmd or "pnpm test" in cmd


class PlaywrightAdapter(RegexTestAdapter):
    name = "playwright"
    patterns = [r"^\s*✘\s+\d+\s+(.+)$"]

    def can_handle_command(self, command: str) -> bool:
        return "playwright" in (command or "")


class MavenSurefireAdapter(RegexTestAdapter):
    name = "maven-surefire"
    patterns = [r"^\s*\[ERROR\]\s+(.+)\s+Time elapsed:.+$"]

    def can_handle_command(self, command: str) -> bool:
        cmd = command or ""
        return "mvn test" in cmd or "maven" in cmd


class GoTestAdapter(RegexTestAdapter):
    name = "go-test"
    patterns = [r"^\s*--- FAIL:\s+([^(]+)"]

    def can_handle_command(self, command: str) -> bool:
        return "go test" in (command or "")


def _extract_with_patterns(log_excerpt: Optional[str], patterns: List[str]) -> List[str]:
    if not log_excerpt:
        return []
    names = set()
    for line in log_excerpt.splitlines():
        for pattern in patterns:
            m = re.match(pattern, line, re.IGNORECASE)
            if m:
                names.add(m.group(1).strip())
    return list(names)[:50]


def auto_detect_test_adapter(command: Optional[str]) -> TestAdapter:
    adapters: List[TestAdapter] = [
        PytestAdapter(),
        JestAdapter(),
        PlaywrightAdapter(),
        MavenSurefireAdapter(),
        GoTestAdapter(),
        RegexTestAdapter(),
    ]
    cmd = command or ""
    for adapter in adapters:
        if adapter.can_handle_command(cmd):
            return adapter
    return RegexTestAdapter()


def register_builtin_test_adapters() -> None:
    register_test_adapter(PytestAdapter())
    register_test_adapter(JestAdapter())
    register_test_adapter(PlaywrightAdapter())
    register_test_adapter(MavenSurefireAdapter())
    register_test_adapter(GoTestAdapter())
    register_test_adapter(RegexTestAdapter())
