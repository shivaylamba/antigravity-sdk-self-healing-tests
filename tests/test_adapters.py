from src.adapters.providers import GitHubActionsAdapter, ManualAdapter, auto_detect_provider
from src.adapters.tests import PytestAdapter, auto_detect_test_adapter


def test_provider_detection_prefers_github():
    adapter = auto_detect_provider({"GITHUB_ACTIONS": "true"})
    assert isinstance(adapter, GitHubActionsAdapter)


def test_provider_detection_falls_back_manual():
    adapter = auto_detect_provider({})
    assert isinstance(adapter, ManualAdapter)


def test_test_adapter_detection_pytest():
    adapter = auto_detect_test_adapter("pytest")
    assert isinstance(adapter, PytestAdapter)
    failed = adapter.infer_failed_tests(
        "\n".join(
            [
                "FAILED path/to/test_file.py::test_name - AssertionError",
                "FAILED path/to/test_file.py::test_special_name[param-1] - ValueError",
            ]
        )
    )
    assert "path/to/test_file.py::test_name" in failed
    assert "path/to/test_file.py::test_special_name[param-1]" in failed


def test_pytest_adapter_non_matching_pattern():
    adapter = PytestAdapter()
    failed = adapter.infer_failed_tests("some unrelated log line")
    assert failed == []
