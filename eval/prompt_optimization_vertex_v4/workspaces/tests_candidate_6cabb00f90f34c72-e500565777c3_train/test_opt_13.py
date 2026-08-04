# file: src\sample_repo\isort\isort\deprecated\finders.py:167-199
# asked: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 196], [195, 198]]}
# gained: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 196], [195, 198]]}

import os
import sysconfig
from pathlib import Path
from isort import sections
from isort.deprecated.finders import PathFinder
from isort.settings import Config


def test_path_finder_find_branches(tmp_path):
    # Setup directories and files to trigger various paths in PathFinder.find
    # 1. site-packages / dist-packages -> THIRDPARTY (line 182-186)
    sp_dir = tmp_path / "site-packages"
    sp_dir.mkdir()
    mod_sp = sp_dir / "mod_sp.py"
    mod_sp.write_text("# module")

    # 2. stdlib_lib_prefix -> STDLIB (line 187-188, and starts_with prefix line 195-196)
    stdlib_path = sysconfig.get_paths()["stdlib"]
    stdlib_dir = Path(stdlib_path)

    # 3. conda_env -> THIRDPARTY (line 189-190)
    conda_dir = tmp_path / "conda_env" / "lib"
    conda_dir.mkdir(parents=True)

    # 4. FIRSTPARTY via src_paths (line 191-193)
    root_dir = tmp_path / "root"
    src_dir = root_dir / "src"
    pkg_dir = src_dir / "my_first_party"
    pkg_dir.mkdir(parents=True)
    init_file = pkg_dir / "__init__.py"
    init_file.write_text("# package")

    # 5. default_section (line 198)
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    mod_other = other_dir / "mod_other.py"
    mod_other.write_text("# module")

    # Configure Config
    config = Config(
        src_paths=[str(src_dir.resolve())],
        default_section="DEFAULT_SECTION",
    )

    finder = PathFinder(config, path=str(root_dir))
    
    # Override self.paths and attributes to explicitly exercise lines 167-199
    finder.paths = [
        str(sp_dir),
        str(stdlib_dir),
        str(conda_dir),
        str(other_dir),
        str(root_dir),
    ]
    finder.conda_env = str(conda_dir.parent)
    finder.stdlib_lib_prefix = os.path.normcase(str(stdlib_dir))

    # Test site-packages -> THIRDPARTY
    assert finder.find("mod_sp") == sections.THIRDPARTY

    # Test stdlib -> STDLIB (exact normcase match)
    fake_stdlib = tmp_path / "stdlib_fake"
    fake_stdlib.mkdir()
    (fake_stdlib / "os.py").write_text("# stdlib")
    finder.paths = [str(fake_stdlib)]
    finder.stdlib_lib_prefix = os.path.normcase(str(fake_stdlib))
    assert finder.find("os") == sections.STDLIB

    # Test stdlib startswith -> STDLIB (line 195-196)
    sub_stdlib = fake_stdlib / "sub"
    sub_stdlib.mkdir()
    (sub_stdlib / "submod.py").write_text("# sub stdlib")
    finder.paths = [str(sub_stdlib)]
    finder.stdlib_lib_prefix = os.path.normcase(str(fake_stdlib))
    assert finder.find("submod") == sections.STDLIB

    # Test conda_env -> THIRDPARTY
    mod_conda = conda_dir / "mod_conda.py"
    mod_conda.write_text("# conda")
    finder.paths = [str(conda_dir)]
    finder.conda_env = str(conda_dir.parent)
    assert finder.find("mod_conda") == sections.THIRDPARTY

    # Test FIRSTPARTY
    finder.paths = [str(src_dir)]
    finder.conda_env = ""
    finder.stdlib_lib_prefix = "nonexistent"
    assert finder.find("my_first_party") == sections.FIRSTPARTY

    # Test default_section (no condition met)
    finder.paths = [str(other_dir)]
    assert finder.find("mod_other") == "DEFAULT_SECTION"

    # Test module not found -> returns None (line 199)
    finder.paths = [str(other_dir)]
    assert finder.find("nonexistent_module") is None
