from .providers import auto_detect_provider, register_builtin_provider_adapters
from .tests import auto_detect_test_adapter, register_builtin_test_adapters
from .vcs import register_builtin_vcs_adapters


def register_builtin_adapters() -> None:
    register_builtin_provider_adapters()
    register_builtin_test_adapters()
    register_builtin_vcs_adapters()
