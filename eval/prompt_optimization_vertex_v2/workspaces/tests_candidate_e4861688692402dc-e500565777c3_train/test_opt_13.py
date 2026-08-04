# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_files():
    # Clear cache to ensure clean execution state
    RequirementsFinder._get_files_from_dir_cached.cache_clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Case 1: File/dir without "requirements" in name (should be skipped)
        ignored_file = os.path.join(tmpdir, "other.txt")
        with open(ignored_file, "w") as f:
            f.write("some content")

        ignored_dir = os.path.join(tmpdir, "other_dir")
        os.makedirs(ignored_dir)

        # Case 2: Directory with "requirements" in name containing subfiles (matching and non-matching extensions)
        reqs_dir = os.path.join(tmpdir, "requirements_sub")
        os.makedirs(reqs_dir)
        
        valid_subfile = os.path.join(reqs_dir, "base.txt")
        with open(valid_subfile, "w") as f:
            f.write("django")

        invalid_subfile = os.path.join(reqs_dir, "base.py")
        with open(invalid_subfile, "w") as f:
            f.write("import os")

        # Case 3: File with "requirements" in name (matching and non-matching extensions)
        valid_req_file = os.path.join(tmpdir, "requirements.txt")
        with open(valid_req_file, "w") as f:
            f.write("requests")

        invalid_req_file = os.path.join(tmpdir, "requirements.log")
        with open(invalid_req_file, "w") as f:
            f.write("logs")

        # Call the cached method
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Assertions
        # Should include valid subfile inside requirements directory and valid requirements file
        assert valid_subfile in results
        assert valid_req_file in results
        assert invalid_subfile not in results
        assert invalid_req_file not in results
        assert ignored_file not in results

        # Test cache hit by calling it again
        results_cached = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert results_cached == results

    # Clean up cache
    RequirementsFinder._get_files_from_dir_cached.cache_clear()
