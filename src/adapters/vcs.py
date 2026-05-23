from typing import Optional

from .base import VCSAdapter
from .registry import register_vcs_adapter


class GitHubVCSAdapter:
    name = "github"

    def create_change_request(self, title: str, body: str, branch: str) -> Optional[str]:
        return None


class GitLabVCSAdapter:
    name = "gitlab"

    def create_change_request(self, title: str, body: str, branch: str) -> Optional[str]:
        return None


class NoopVCSAdapter:
    name = "none"

    def create_change_request(self, title: str, body: str, branch: str) -> Optional[str]:
        return None


def register_builtin_vcs_adapters() -> None:
    register_vcs_adapter(GitHubVCSAdapter())
    register_vcs_adapter(GitLabVCSAdapter())
    register_vcs_adapter(NoopVCSAdapter())
