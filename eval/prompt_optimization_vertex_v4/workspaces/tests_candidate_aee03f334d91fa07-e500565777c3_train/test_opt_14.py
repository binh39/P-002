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
        # 1. File without "requirements" in name (should be skipped)
        other_file = os.path.join(tmpdir, "random.txt")
        with open(other_file, "w") as f:
            f.write("some content")

        # 2. File with "requirements" in name, matching extension (should be included via os.path.isfile branch)
        req_file = os.path.join(tmpdir, "requirements.txt")
        with open(req_file, "w") as f:
            f.write("django")

        # 3. File with "requirements" in name, NOT matching extension (should not be added)
        req_wrong_ext = os.path.join(tmpdir, "requirements.cfg")
        with open(req_wrong_ext, "w") as f:
            f.write("django")

        # 4. Directory with "requirements" in name, containing files with matching/non-matching extensions (os.path.isdir branch)
        req_dir = os.path.join(tmpdir, "requirements-dev")
        os.makedirs(req_dir)

        sub_match = os.path.join(req_dir, "base.txt")
        with open(sub_match, "w") as f:
            f.write("pytest")

        sub_no_match = os.path.join(req_dir, "base.md")
        with open(sub_no_match, "w") as f:
            f.write("markdown")

        # Call the method
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Assertions
        assert req_file in results
        assert sub_match in results
        assert other_file not in results
        assert req_wrong_ext not in results
        assert sub_no_match not in results

        # Test cache hit by calling it again
        cached_results = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert cached_results == results

    # Cleanup cache
    RequirementsFinder._get_files_from_dir_cached.cache_clear()
