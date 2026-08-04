# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_files():
    # Clear cache to ensure clean run
    RequirementsFinder._get_files_from_dir_cached.cache_clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. File without "requirements" in name (should be skipped)
        ignored_file = os.path.join(tmpdir, "random.txt")
        with open(ignored_file, "w") as f:
            f.write("pytest")

        # 2. File with "requirements" in name but wrong extension (should be skipped by isfile/ext check)
        wrong_ext_file = os.path.join(tmpdir, "requirements.log")
        with open(wrong_ext_file, "w") as f:
            f.write("pytest")

        # 3. File with "requirements" and valid extension (.txt)
        req_file_txt = os.path.join(tmpdir, "requirements.txt")
        with open(req_file_txt, "w") as f:
            f.write("pytest")

        # 4. File with "requirements" and valid extension (.in)
        req_file_in = os.path.join(tmpdir, "requirements.in")
        with open(req_file_in, "w") as f:
            f.write("pytest")

        # 5. Directory containing "requirements" with subfiles (matching and non-matching)
        req_dir = os.path.join(tmpdir, "requirements_dir")
        os.mkdir(req_dir)
        
        sub_txt = os.path.join(req_dir, "base.txt")
        with open(sub_txt, "w") as f:
            f.write("pytest")

        sub_log = os.path.join(req_dir, "other.log")
        with open(sub_log, "w") as f:
            f.write("pytest")

        # Call the cached method which exercises lines 298-325
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Normalize paths for comparison
        normalized_results = {os.path.normpath(r) for r in results}
        expected = {
            os.path.normpath(req_file_txt),
            os.path.normpath(req_file_in),
            os.path.normpath(sub_txt),
        }

        assert normalized_results == expected

        # Call it again to hit the lru_cache hit path
        cached_results = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert {os.path.normpath(r) for r in cached_results} == expected

    # Clean up cache
    RequirementsFinder._get_files_from_dir_cached.cache_clear()
