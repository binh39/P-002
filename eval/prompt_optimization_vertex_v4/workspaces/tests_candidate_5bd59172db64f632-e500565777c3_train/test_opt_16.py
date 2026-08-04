# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create various files and directories to test all branches in _get_files_from_dir_cached
        
        # 1. File without "requirements" in name (should be skipped)
        with open(os.path.join(tmpdir, "random.txt"), "w") as f:
            f.write("")

        # 2. File with "requirements" in name and valid extension (should be included)
        req_file_txt = os.path.join(tmpdir, "requirements.txt")
        with open(req_file_txt, "w") as f:
            f.write("")

        # 3. File with "requirements" in name but invalid extension (should not be added)
        req_file_invalid = os.path.join(tmpdir, "requirements.log")
        with open(req_file_invalid, "w") as f:
            f.write("")

        # 4. Directory with "requirements" in name containing valid extension files
        req_dir = os.path.join(tmpdir, "requirements_dir")
        os.mkdir(req_dir)
        sub_txt = os.path.join(req_dir, "base.txt")
        with open(sub_txt, "w") as f:
            f.write("")
        sub_in = os.path.join(req_dir, "dev.in")
        with open(sub_in, "w") as f:
            f.write("")
        sub_invalid = os.path.join(req_dir, "other.log")
        with open(sub_invalid, "w") as f:
            f.write("")

        # Clear cache to ensure execution
        RequirementsFinder._get_files_from_dir_cached.cache_clear()

        # Call the cached method
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Normalize paths for comparison
        results_normalized = {os.path.normpath(p) for p in results}
        expected = {os.path.normpath(req_file_txt), os.path.normpath(sub_txt), os.path.normpath(sub_in)}

        assert results_normalized == expected
        
        # Also test cache hit by calling it a second time
        results_cached = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert {os.path.normpath(p) for p in results_cached} == expected
        
        # Clean cache after test
        RequirementsFinder._get_files_from_dir_cached.cache_clear()
