# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Clear lru_cache to be sure
        RequirementsFinder._get_files_from_dir_cached.cache_clear()

        # Create files and directories that match/don't match requirements criteria
        # 1. File that does not have "requirements" in name
        unrelated_file = os.path.join(tmpdir, "setup.txt")
        with open(unrelated_file, "w") as f:
            f.write("content")

        # 2. File matching requirements with valid extension (e.g. .txt)
        req_file = os.path.join(tmpdir, "requirements.txt")
        with open(req_file, "w") as f:
            f.write("content")

        # 3. File matching requirements with invalid extension
        req_invalid_ext = os.path.join(tmpdir, "requirements.log")
        with open(req_invalid_ext, "w") as f:
            f.write("content")

        # 4. Directory containing requirements with valid subfile
        req_dir = os.path.join(tmpdir, "requirements_dir")
        os.mkdir(req_dir)
        sub_req_file = os.path.join(req_dir, "base.in")
        with open(sub_req_file, "w") as f:
            f.write("content")

        # 5. Directory containing requirements with invalid subfile
        sub_invalid_file = os.path.join(req_dir, "base.log")
        with open(sub_invalid_file, "w") as f:
            f.write("content")

        # Call the cached method
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Assertions
        assert req_file in results
        assert sub_req_file in results
        assert unrelated_file not in results
        assert req_invalid_ext not in results
        assert sub_invalid_file not in results

        # Test cache hit
        results_cached = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert results_cached == results

        # Clean up cache
        RequirementsFinder._get_files_from_dir_cached.cache_clear()
