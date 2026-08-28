from fixture312 import dependency_version


def test_project_312_dependency():
    assert dependency_version() == "25.0"
