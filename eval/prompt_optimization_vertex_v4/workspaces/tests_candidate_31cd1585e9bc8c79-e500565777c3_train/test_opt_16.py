# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_methods():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create various files and directories to exercise all branches of _get_files_from_dir_cached
        
        # 1. File without "requirements" in name (should be skipped)
        other_file = os.path.join(tmpdir, "random.txt")
        with open(other_file, "w") as f:
            f.write("")

        # 2. File with "requirements" in name but valid extension (should match)
        req_file = os.path.join(tmpdir, "requirements.txt")
        with open(req_file, "w") as f:
            f.write("")

        # 3. File with "requirements" in name but invalid extension (should not match)
        req_invalid_ext = os.path.join(tmpdir, "requirements.log")
        with open(req_invalid_ext, "w") as f:
            f.write("")

        # 4. Directory with "requirements" in name containing files with valid and invalid extensions
        req_dir = os.path.join(tmpdir, "requirements_dir")
        os.mkdir(req_dir)
        
        sub_valid_txt = os.path.join(req_dir, "base.txt")
        with open(sub_valid_txt, "w") as f:
            f.write("")

        sub_valid_in = os.path.join(req_dir, "dev.in")
        with open(sub_valid_in, "w") as f:
            f.write("")

        sub_invalid = os.path.join(req_dir, "other.cfg")
        with open(sub_invalid, "w") as f:
            f.write("")

        # Clear cache to ensure clean execution
        RequirementsFinder._get_files_from_dir_cached.cache_clear()

        # Call the cached method
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Normalize paths for platform-independent assertion
        normalized_results = {os.path.normpath(p) for p in results}
        expected = {
            os.path.normpath(req_file),
            os.path.normpath(sub_valid_txt),
            os.path.normpath(sub_valid_in),
        }

        assert expected.issubset(normalized_results)
        assert os.path.normpath(other_file) not in normalized_results
        assert os.path.normpath(req_invalid_ext) not in normalized_results
        assert os.path.normpath(sub_invalid) not in normalized_results

        # Test cache hit by calling again
        cached_results = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert cached_results == results

        # Clean up cache
        RequirementsFinder._get_files_from_dir_cached.cache_clear()
