# file: src\sample_repo\isort\isort\place.py:64-96
# asked: {"lines": [64, 65, 66, 67, 68, 69, 70, 71, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 88, 90, 91, 92, 94, 96], "branches": [[70, 71], [70, 73], [77, 78], [77, 96], [79, 80], [79, 81], [81, 88], [81, 89], [89, 77], [89, 94]]}
# gained: {"lines": [64, 67, 68, 69, 70, 71, 73, 74, 75, 77, 78, 79, 80, 81, 90, 91, 92, 94, 96], "branches": [[70, 71], [70, 73], [77, 78], [77, 96], [79, 80], [79, 81], [81, 89], [89, 77], [89, 94]]}

import tempfile
from pathlib import Path
import pytest

from isort import sections
from isort.place import _src_path
from isort.settings import Config


@pytest.fixture
def custom_tmp_path():
    d = tempfile.TemporaryDirectory()
    try:
        yield Path(d.name)
    finally:
        d.cleanup()


def test_src_path_basic(custom_tmp_path: Path):
    mod_file = custom_tmp_path / "mymod.py"
    mod_file.write_text("print('hello')")

    config = Config(src_paths=[custom_tmp_path])
    res = _src_path("mymod", config)
    assert res == (sections.FIRSTPARTY, f"Found in one of the configured src_paths: {custom_tmp_path}.")


def test_src_path_with_explicit_src_paths(custom_tmp_path: Path):
    sub_path = custom_tmp_path / "subdir"
    sub_path.mkdir()
    mod_file = sub_path / "submod.py"
    mod_file.write_text("print('sub')")

    config = Config()
    res = _src_path("submod", config, src_paths=[sub_path])
    assert res == (sections.FIRSTPARTY, f"Found in one of the configured src_paths: {sub_path}.")


def test_src_path_prefix_condition(custom_tmp_path: Path):
    named_dir = custom_tmp_path / "mypkg"
    named_dir.mkdir()
    init_file = named_dir / "__init__.py"
    init_file.write_text("")

    config = Config(src_paths=[named_dir])
    res = _src_path("mypkg", config)
    assert res == (sections.FIRSTPARTY, f"Found in one of the configured src_paths: {named_dir}.")








def test_src_path_returns_none(custom_tmp_path: Path):
    config = Config(src_paths=[custom_tmp_path])
    res = _src_path("nonexistent", config)
    assert res is None
