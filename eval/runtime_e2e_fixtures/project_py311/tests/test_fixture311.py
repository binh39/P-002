from fixture311 import dependency_version


def test_project_311_dependency():
    assert dependency_version() == "24.2"
