# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_files():
    # Clear the lru_cache for a clean test run
    RequirementsFinder._get_files_from_dir_cached.cache_clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create various files and directories to exercise all branches:
        # 1. File without "requirements" in name (should be skipped)
        unrelated_file = os.path.join(tmpdir, "setup.txt")
        with open(unrelated_file, "w") as f:
            f.write("")

        # 2. File with "requirements" in name but invalid extension (should be skipped)
        invalid_ext_file = os.path.join(tmpdir, "requirements.cfg")
        with open(invalid_ext_file, "w") as f:
            f.write("")

        # 3. File with "requirements" in name and valid extension (.txt)
        valid_file = os.path.join(tmpdir, "requirements.txt")
        with open(valid_file, "w") as f:
            f.write("")

        # 4. Another file with valid extension (.in)
        valid_in_file = os.path.join(tmpdir, "dev-requirements.in")
        with open(valid_in_file, "w") as f:
            f.write("")

        # 5. Directory with "requirements" in name containing subfiles (some matching ext, some not)
        req_dir = os.path.join(tmpdir, "requirements-sub")
        os.mkdir(req_dir)
        
        sub_valid_txt = os.path.join(req_dir, "base.txt")
        with open(sub_valid_txt, "w") as f:
            f.write("")

        sub_invalid_ext = os.path.join(req_dir, "base.cfg")
        with open(sub_invalid_ext, "w") as f:
            f.write("")

        # Call the cached method
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Normalize paths for platform-agnostic comparison
        normalized_results = {os.path.normpath(p) for p in results}

        expected = {
            os.path.normpath(valid_file),
            os.path.normpath(valid_in_file),
            os.path.normpath(sub_valid_txt),
        }

        assert normalized_results == expected

        # Test cache hit branch
        cached_results = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert {os.path.normpath(p) for p in cached_results} == expected

    # Clean up cache
    RequirementsFinder._get_files_from_dir_cached.cache_clear()
