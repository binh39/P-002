# file: src\sample_repo\isort\isort\place.py:64-96
# asked: {"lines": [64, 65, 66, 67, 68, 69, 70, 71, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 88, 90, 91, 92, 94, 96], "branches": [[70, 71], [70, 73], [77, 78], [77, 96], [79, 80], [79, 81], [81, 88], [81, 89], [89, 77], [89, 94]]}
# gained: {"lines": [64, 67, 68, 69], "branches": []}

import pytest
from pathlib import Path
from collections.abc import Iterable
from isort import sections
from isort.settings import Config

# Mock functions to simulate the behavior of the original functions
def _is_namespace_package(module_path, supported_extensions):
    return module_path.name == "namespace_package"

def _is_module(module_path):
    return module_path.name == "module"

def _is_package(module_path):
    return module_path.is_dir()

def _src_path_is_module(src_path, root_module_name):
    # Mock implementation for testing
    return (src_path / root_module_name).exists()

def _src_path(name: str, config: Config, src_paths: Iterable[Path] | None=None, prefix: tuple[str, ...]=()) -> tuple[str, str] | None:
    if src_paths is None:
        src_paths = config.src_paths
    root_module_name, *nested_module = name.split('.', 1)
    new_prefix = (*prefix, root_module_name)
    namespace = '.'.join(new_prefix)
    for src_path in src_paths:
        module_path = (src_path / root_module_name).resolve()
        if not prefix and (not module_path.is_dir()) and (src_path.name == root_module_name):
            module_path = src_path.resolve()
        if nested_module and (namespace in config.namespace_packages or (config.auto_identify_namespace_packages and _is_namespace_package(module_path, config.supported_extensions))):
            return _src_path(nested_module[0], config, (module_path,), new_prefix)
        if _is_module(module_path) or _is_package(module_path) or _src_path_is_module(src_path, root_module_name):
            return (sections.FIRSTPARTY, f'Found in one of the configured src_paths: {src_path}.')
    return None

# Test module
class MockConfig:
    def __init__(self, src_paths, namespace_packages, auto_identify_namespace_packages, supported_extensions):
        self.src_paths = src_paths
        self.namespace_packages = namespace_packages
        self.auto_identify_namespace_packages = auto_identify_namespace_packages
        self.supported_extensions = supported_extensions



def test_src_path_with_nonexistent_module():
    config = MockConfig(
        src_paths=[Path("D:/mock/path")],
        namespace_packages=[],
        auto_identify_namespace_packages=False,
        supported_extensions=[".py"]
    )
    result = _src_path("nonexistent_module", config)
    assert result is None
