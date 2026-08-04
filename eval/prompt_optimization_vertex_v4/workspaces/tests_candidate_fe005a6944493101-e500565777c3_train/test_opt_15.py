# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_get_files_from_dir_cached(tmp_path):
    # Setup files and directories to exercise all branches in _get_files_from_dir_cached:
    # 1. File without "requirements" in name (should be skipped)
    # 2. File with "requirements" in name but not matching exts (should not match isfile ext loop or be added)
    # 3. File with "requirements" in name and matching ext (e.g. requirements.txt)
    # 4. Directory with "requirements" in name containing a file matching exts (e.g. subfile.txt)
    # 5. Directory with "requirements" in name containing a file NOT matching exts

    # Clear cache to start fresh
    RequirementsFinder._get_files_from_dir_cached.cache_clear()

    # Create test structure
    other_file = tmp_path / "other.txt"
    other_file.write_text("content")

    req_wrong_ext = tmp_path / "requirements.dat"
    req_wrong_ext.write_text("content")

    req_file_txt = tmp_path / "requirements.txt"
    req_file_txt.write_text("content")

    req_file_in = tmp_path / "requirements_dev.in"
    req_file_in.write_text("content")

    req_dir = tmp_path / "my_requirements_dir"
    req_dir.mkdir()
    sub_txt = req_dir / "subfile.txt"
    sub_txt.write_text("content")
    sub_dat = req_dir / "subfile.dat"
    sub_dat.write_text("content")

    # Call the cached method
    results = RequirementsFinder._get_files_from_dir_cached(str(tmp_path))

    # Assertions
    # Should include requirements.txt, requirements_dev.in, and req_dir/subfile.txt
    # Should NOT include other.txt, requirements.dat, or req_dir/subfile.dat
    expected_files = {
        str(req_file_txt),
        str(req_file_in),
        str(sub_txt),
    }

    assert set(results) == expected_files

    # Call a second time to ensure cache hit works and returns the same results
    results_cached = RequirementsFinder._get_files_from_dir_cached(str(tmp_path))
    assert set(results_cached) == expected_files

    # Clean up cache
    RequirementsFinder._get_files_from_dir_cached.cache_clear()
