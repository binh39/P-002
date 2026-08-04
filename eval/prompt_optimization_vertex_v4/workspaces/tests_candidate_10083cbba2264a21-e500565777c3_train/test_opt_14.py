# file: src\sample_repo\isort\isort\deprecated\finders.py:167-199
# asked: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 196], [195, 198]]}
# gained: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 198]]}

import os
import sysconfig
from pathlib import Path
from isort import sections
from isort.deprecated.finders import PathFinder
from isort.settings import Config


def test_path_finder_find_branches(tmp_path):
    # Setup directories and files
    root = tmp_path / "project"
    root.mkdir()

    # 1. site-packages / dist-packages branch (THIRDPARTY)
    site_pkg = tmp_path / "site-packages"
    site_pkg.mkdir()
    mod_site = site_pkg / "mod_site.py"
    mod_site.write_text("")

    # 2. stdlib_lib_prefix branch (STDLIB)
    stdlib_path = Path(sysconfig.get_paths()["stdlib"])

    # 3. conda_env branch (THIRDPARTY)
    conda_dir = tmp_path / "conda"
    conda_dir.mkdir()
    mod_conda = conda_dir / "mod_conda.py"
    mod_conda.write_text("")

    # 4. src_paths branch (FIRSTPARTY)
    src_dir = root / "src"
    src_dir.mkdir()
    sub_pkg = src_dir / "sub_pkg"
    sub_pkg.mkdir()
    (sub_pkg / "__init__.py").write_text("")

    # 5. virtual_env with virtual_env_src branch (THIRDPARTY)
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    venv_src = venv_dir / "src" / "my_venv_mod"
    venv_src.mkdir(parents=True)
    (venv_src / "__init__.py").write_text("")

    # 6. stdlib_lib_prefix startswith branch (STDLIB)
    # The stdlib_path itself or a subpath starting with stdlib_lib_prefix
    # Let's create a temporary dir inside or alongside stdlib if possible, or mock/set stdlib_lib_prefix
    # Or test with an extension suffix / __init__.py inside site-packages / stdlib etc.

    config = Config(src_paths=[str(src_dir)])
    finder = PathFinder(config, path=str(root))

    # Manually inject our custom test paths into finder.paths to hit all specific conditional returns
    finder.paths = [
        str(site_pkg),
        str(conda_dir),
        str(venv_dir / "src"),
        str(sub_pkg.parent),  # parent of sub_pkg is src_dir, which is in src_paths
        str(stdlib_path),
        str(root),
    ]
    finder.virtual_env = str(venv_dir)
    finder.virtual_env_src = str(venv_dir / "src") + "/"
    finder.conda_env = str(conda_dir)
    finder.stdlib_lib_prefix = os.path.normcase(str(stdlib_path))

    # Test site-packages -> THIRDPARTY
    assert finder.find("mod_site") == sections.THIRDPARTY

    # Test conda_env -> THIRDPARTY
    assert finder.find("mod_conda") == sections.THIRDPARTY

    # Test virtual_env and virtual_env_src in prefix -> THIRDPARTY
    # venv_src is inside venv_dir / "src", prefix contains virtual_env_src
    finder.paths = [str(venv_src.parent)]
    assert finder.find("my_venv_mod") == sections.THIRDPARTY

    # Test stdlib_lib_prefix -> STDLIB
    # Create a dummy file in stdlib or test with an existing module if possible, or mock exists_case_sensitive / paths
    # Alternatively, create a file in stdlib_path if writable, or just rely on a path matching stdlib_lib_prefix
    stdlib_mod = stdlib_path / "test_stdlib_mod.py"
    try:
        stdlib_mod.write_text("")
    except OSError:
        pass  # If stdlib is read-only, we can test via mocking or setting stdlib_lib_prefix to a writable temp path
    
    if stdlib_mod.exists():
        finder.paths = [str(stdlib_path)]
        finder.stdlib_lib_prefix = os.path.normcase(str(stdlib_path))
        assert finder.find("test_stdlib_mod") == sections.STDLIB
        stdlib_mod.unlink(missing_ok=True)
    else:
        # Test stdlib startswith branch or exact match using temp path as stdlib prefix
        custom_stdlib = tmp_path / "custom_stdlib"
        custom_stdlib.mkdir()
        (custom_stdlib / "os.py").write_text("")
        finder.paths = [str(custom_stdlib)]
        finder.stdlib_lib_prefix = os.path.normcase(str(custom_stdlib))
        assert finder.find("os") == sections.STDLIB
        # Also test .startswith(stdlib_lib_prefix) where prefix has a trailing subpath
        sub_custom_stdlib = custom_stdlib / "sub"
        sub_custom_stdlib.mkdir()
        (sub_custom_stdlib / "submod.py").write_text("")
        finder.paths = [str(sub_custom_stdlib)]
        assert finder.find("submod") == sections.STDLIB

    # Test src_paths -> FIRSTPARTY
    finder.paths = [str(sub_pkg.parent)]
    finder.config.is_skipped = lambda p: False
    assert finder.find("sub_pkg") == sections.FIRSTPARTY

    # Test default section fallback
    plain_dir = tmp_path / "plain"
    plain_dir.mkdir()
    (plain_dir / "plainmod.py").write_text("")
    finder.paths = [str(plain_dir)]
    finder.stdlib_lib_prefix = "nonexistent_stdlib"
    assert finder.find("plainmod") == config.default_section

    # Test module not found -> None
    finder.paths = [str(plain_dir)]
    assert finder.find("nonexistent") is None
