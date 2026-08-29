from cloud.sandbox_contract import RunnerProfile
from cloud.sandbox_runner_profiles import select_runner_profile


def test_project_native_profile_preserves_project_versions():
    packages = {"pytest": "8.4.2", "coverage": "7.10.7", "pytest-asyncio": "1.1.0"}

    decision = select_runner_profile(packages)

    assert decision.profile == RunnerProfile.PROJECT_NATIVE
    assert decision.pytest_version == "8.4.2"
    assert decision.coverage_version == "7.10.7"
    assert packages == {"pytest": "8.4.2", "coverage": "7.10.7", "pytest-asyncio": "1.1.0"}


def test_sandbox_managed_profile_is_used_only_when_project_has_no_runner_packages():
    decision = select_runner_profile({"project-dependency": "2.0"})

    assert decision.profile == RunnerProfile.SANDBOX_MANAGED
    assert decision.pytest_version is not None
    assert decision.coverage_version is not None


def test_partial_project_runner_uses_actionable_fallback_without_injection():
    decision = select_runner_profile({"pytest": "8.4.2"})

    assert decision.profile == RunnerProfile.COMPATIBILITY_FALLBACK
    assert decision.error_code == "INCOMPLETE_PROJECT_RUNNER"
    assert "coverage" in decision.reason


def test_unsupported_project_runner_uses_actionable_fallback():
    decision = select_runner_profile({"pytest": "6.2.5", "coverage": "6.5.0"})

    assert decision.profile == RunnerProfile.COMPATIBILITY_FALLBACK
    assert decision.error_code == "UNSUPPORTED_PROJECT_RUNNER"


def test_package_names_are_normalized_without_mutating_input():
    packages = {"PyTest": "9.1.1", "coverage": "7.15.2", "pytest_asyncio": "1.4.0"}

    decision = select_runner_profile(packages)

    assert decision.profile == RunnerProfile.PROJECT_NATIVE
    assert packages["pytest_asyncio"] == "1.4.0"
