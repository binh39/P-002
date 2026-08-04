# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached():
    # Clear cache to ensure fresh execution
    RequirementsFinder._get_files_from_dir_cached.cache_clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Case 1: File/Dir without "requirements" in name (should be skipped by line 304/305)
        ignored_file = os.path.join(tmpdir, "random.txt")
        with open(ignored_file, "w") as f:
            f.write("test")

        ignored_dir = os.path.join(tmpdir, "random_dir")
        os.makedirs(ignored_dir)

        # Case 2: A directory with "requirements" in its name containing matching and non-matching extension files
        req_dir = os.path.join(tmpdir, "requirements_dir")
        os.makedirs(req_dir)
        sub_txt = os.path.join(req_dir, "base.txt")
        sub_in = os.path.join(req_dir, "dev.in")
        sub_other = os.path.join(req_dir, "other.py")
        for p in (sub_txt, sub_in, sub_other):
            with open(p, "w") as f:
                f.write("test")

        # Case 3: A file with "requirements" in its name with matching and non-matching extensions
        req_file_txt = os.path.join(tmpdir, "requirements.txt")
        with open(req_file_txt, "w") as f:
            f.write("test")

        req_file_other = os.path.join(tmpdir, "requirements.py")
        with open(req_file_other, "w") as f:
            f.write("test")

        # Run the cached method
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Assertions
        # Should include sub_txt, sub_in, and req_file_txt
        # Should NOT include ignored_file, ignored_dir, sub_other, req_file_other
        assert sub_txt in results
        assert sub_in in results
        assert req_file_txt in results
        assert sub_other not in results
        assert req_file_other not in results
        assert ignored_file not in results
        assert ignored_dir not in results

        # Test lru_cache hit
        results_cached = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert results == results_cached

    RequirementsFinder._get_files_from_dir_cached.cache_clear()
