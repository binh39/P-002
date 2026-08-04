# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_paths(tmp_path):
    # Clear the lru_cache for deterministic behavior
    RequirementsFinder._get_files_from_dir_cached.cache_clear()

    # Create directory structure to exercise lines 298-325:
    # 1. File without "requirements" in name (skipped)
    # 2. File with "requirements" in name, but not matching exts (skipped)
    # 3. File with "requirements" in name and matching ext (e.g. requirements.txt) -> matches isfile branch
    # 4. Directory with "requirements" in name containing subfiles matching exts -> matches isdir branch
    # 5. Directory with "requirements" in name containing subfiles not matching exts

    # 1. Non-matching file
    (tmp_path / "other.txt").write_text("content")

    # 2. Requirements file with unsupported extension
    (tmp_path / "requirements.log").write_text("content")

    # 3. Requirements file with supported extension (.txt)
    req_file_txt = tmp_path / "requirements.txt"
    req_file_txt.write_text("content")

    # Also test another supported extension (.in) to hit loop termination/break
    req_file_in = tmp_path / "dev-requirements.in"
    req_file_in.write_text("content")

    # 4. Requirements directory containing supported subfiles
    req_dir = tmp_path / "requirements-dir"
    req_dir.mkdir()
    sub_txt = req_dir / "base.txt"
    sub_txt.write_text("content")
    sub_other = req_dir / "base.log"
    sub_other.write_text("content")

    # Call the cached method
    results = RequirementsFinder._get_files_from_dir_cached(str(tmp_path))

    # Normalize paths for assertion across platforms
    results_set = {os.path.normpath(p) for p in results}

    expected = {
        os.path.normpath(str(req_file_txt)),
        os.path.normpath(str(req_file_in)),
        os.path.normpath(str(sub_txt)),
    }

    assert expected.issubset(results_set)
    assert os.path.normpath(str(sub_other)) not in results_set

    # Clean up cache
    RequirementsFinder._get_files_from_dir_cached.cache_clear()
