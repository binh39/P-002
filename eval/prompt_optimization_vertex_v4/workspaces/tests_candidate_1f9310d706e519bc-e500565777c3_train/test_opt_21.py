# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder

def test_requirements_finder_get_files_from_dir_cached():
    # Clear the lru_cache to ensure we exercise the method cleanly
    RequirementsFinder._get_files_from_dir_cached.cache_clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Case 1: File/dir without "requirements" in name (should be skipped)
        os.makedirs(os.path.join(tmpdir, "other_dir"))
        with open(os.path.join(tmpdir, "other_file.txt"), "w") as f:
            f.write("")

        # Case 2: Directory with "requirements" in name containing matching and non-matching files
        req_dir = os.path.join(tmpdir, "requirements_sub")
        os.makedirs(req_dir)
        with open(os.path.join(req_dir, "base.txt"), "w") as f:
            f.write("")
        with open(os.path.join(req_dir, "dev.in"), "w") as f:
            f.write("")
        with open(os.path.join(req_dir, "ignore.dat"), "w") as f:
            f.write("")

        # Case 3: File with "requirements" in name with matching and non-matching extensions
        req_file_txt = os.path.join(tmpdir, "requirements.txt")
        with open(req_file_txt, "w") as f:
            f.write("")
        req_file_in = os.path.join(tmpdir, "requirements_prod.in")
        with open(req_file_in, "w") as f:
            f.write("")
        req_file_bad = os.path.join(tmpdir, "requirements_other.dat")
        with open(req_file_bad, "w") as f:
            f.write("")

        # Call the cached method
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Normalize paths for platform-independent assertion
        normalized_results = {os.path.normpath(p) for p in results}
        expected = {
            os.path.normpath(os.path.join(req_dir, "base.txt")),
            os.path.normpath(os.path.join(req_dir, "dev.in")),
            os.path.normpath(req_file_txt),
            os.path.normpath(req_file_in),
        }

        assert normalized_results == expected

        # Test cache hit coverage as well
        cached_results = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert set(os.path.normpath(p) for p in cached_results) == normalized_results

    RequirementsFinder._get_files_from_dir_cached.cache_clear()
