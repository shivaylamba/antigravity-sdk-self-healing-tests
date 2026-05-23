from typing import Dict, List, Optional, Protocol

from ..types import FailureContext


class CIProviderAdapter(Protocol):
    name: str

    def can_handle(self, environ: Dict[str, str]) -> bool:
        ...

    def build_context(self, cwd: str, environ: Dict[str, str], log_excerpt: Optional[str]) -> FailureContext:
        ...


class TestAdapter(Protocol):
    name: str

    def can_handle_command(self, command: str) -> bool:
        ...

    def infer_failed_tests(self, log_excerpt: Optional[str]) -> List[str]:
        ...


class VCSAdapter(Protocol):
    name: str

    def create_change_request(self, title: str, body: str, branch: str) -> Optional[str]:
        ...
