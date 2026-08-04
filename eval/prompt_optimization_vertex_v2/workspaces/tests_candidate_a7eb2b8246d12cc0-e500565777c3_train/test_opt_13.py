# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create various files and directories to exercise all branches in _get_files_from_dir_cached
        
        # 1. File without "requirements" in name (should be skipped)
        ignored_file = os.path.join(tmpdir, "random.txt")
        with open(ignored_file, "w") as f:
            f.write("")

        # 2. File with "requirements" in name matching extension (should be included)
        req_file = os.path.join(tmpdir, "requirements.txt")
        with open(req_file, "w") as f:
            f.write("")

        # 3. File with "requirements" in name not matching extension (should not match inner ext loop)
        req_bad_ext = os.path.join(tmpdir, "requirements.log")
        with open(req_bad_ext, "w") as f:
            f.write("")

        # 4. Directory with "requirements" in name containing subfiles (should check subfiles and match exts)
        req_dir = os.path.join(tmpdir, "requirements_dir")
        os.mkdir(req_dir)
        
        subfile_match = os.path.join(req_dir, "base.txt")
        with open(subfile_match, "w") as f:
            f.write("")

        subfile_no_match = os.path.join(req_dir, "base.log")
        with open(subfile_no_match, "w") as f:
            f.write("")

        # Clear cache to ensure clean execution of the class method
        RequirementsFinder._get_files_from_dir_cached.cache_clear()

        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Assertions
        assert req_file in results
        assert subfile_match in results
        assert ignored_file not in results
        assert req_bad_ext not in results
        assert subfile_no_match not in results

        # Test cache hit / second call
        results_cached = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert results_cached == results

        RequirementsFinder._get_files_from_dir_cached.cache_clear()
