# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create various files and directories to test different branches in _get_files_from_dir_cached
        
        # 1. File without "requirements" in name (should be skipped)
        ignored_file = os.path.join(tmpdir, "random.txt")
        with open(ignored_file, "w") as f:
            f.write("pytest")

        # 2. File with "requirements" in name and valid extension (should be matched via isfile)
        req_file = os.path.join(tmpdir, "requirements.txt")
        with open(req_file, "w") as f:
            f.write("requests")

        # 3. File with "requirements" in name but invalid extension (should be ignored by isfile loop)
        req_invalid_ext = os.path.join(tmpdir, "requirements.log")
        with open(req_invalid_ext, "w") as f:
            f.write("log")

        # 4. Directory with "requirements" in name (should be processed via isdir)
        req_dir = os.path.join(tmpdir, "requirements_dir")
        os.mkdir(req_dir)

        # Inside req_dir: valid subfile ending with .txt or .in
        sub_valid = os.path.join(req_dir, "base.txt")
        with open(sub_valid, "w") as f:
            f.write("flask")

        # Inside req_dir: invalid subfile ending with something else
        sub_invalid = os.path.join(req_dir, "other.py")
        with open(sub_invalid, "w") as f:
            f.write("print()")

        # Clear cache to ensure execution runs fresh
        RequirementsFinder._get_files_from_dir_cached.cache_clear()

        # Call the cached method
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Assertions
        assert req_file in results
        assert sub_valid in results
        assert ignored_file not in results
        assert req_invalid_ext not in results
        assert sub_invalid not in results

        # Call again to exercise the cache hit path
        results_cached = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert sorted(results) == sorted(results_cached)

        # Cleanup cache
        RequirementsFinder._get_files_from_dir_cached.cache_clear()
