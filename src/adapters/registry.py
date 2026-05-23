from typing import Dict, Optional

from .base import CIProviderAdapter, TestAdapter, VCSAdapter


PROVIDER_ADAPTERS: Dict[str, CIProviderAdapter] = {}
TEST_ADAPTERS: Dict[str, TestAdapter] = {}
VCS_ADAPTERS: Dict[str, VCSAdapter] = {}


def register_provider(adapter: CIProviderAdapter) -> None:
    PROVIDER_ADAPTERS[adapter.name] = adapter


def register_test_adapter(adapter: TestAdapter) -> None:
    TEST_ADAPTERS[adapter.name] = adapter


def register_vcs_adapter(adapter: VCSAdapter) -> None:
    VCS_ADAPTERS[adapter.name] = adapter


def get_provider(name: Optional[str]) -> Optional[CIProviderAdapter]:
    if not name:
        return None
    return PROVIDER_ADAPTERS.get(name)


def get_test_adapter(name: Optional[str]) -> Optional[TestAdapter]:
    if not name:
        return None
    return TEST_ADAPTERS.get(name)


def get_vcs_adapter(name: Optional[str]) -> Optional[VCSAdapter]:
    if not name:
        return None
    return VCS_ADAPTERS.get(name)
