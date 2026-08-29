from packaging.version import Version


def dependency_version() -> str:
    return str(Version("25.0"))
