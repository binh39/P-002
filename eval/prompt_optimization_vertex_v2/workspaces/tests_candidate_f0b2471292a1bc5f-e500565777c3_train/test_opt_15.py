# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_paths():
    # Clear the lru_cache for a clean test state
    RequirementsFinder._get_files_from_dir_cached.cache_clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. File without "requirements" in name (should be skipped by line 304-305)
        other_file = os.path.join(tmpdir, "random.txt")
        with open(other_file, "w") as f:
            f.write("content")

        # 2. File with "requirements" in name but wrong extension (should be checked by line 319-321 and not added)
        wrong_ext_file = os.path.join(tmpdir, "requirements.cfg")
        with open(wrong_ext_file, "w") as f:
            f.write("content")

        # 3. File with "requirements" in name and correct extension (.txt) (should match line 319-323)
        req_txt_file = os.path.join(tmpdir, "requirements.txt")
        with open(req_txt_file, "w") as f:
            f.write("content")

        # 4. File with "requirements" in name and correct extension (.in) (should match line 319-323)
        req_in_file = os.path.join(tmpdir, "prod-requirements.in")
        with open(req_in_file, "w") as f:
            f.write("content")

        # 5. Directory with "requirements" in name (should match line 309-316)
        req_dir = os.path.join(tmpdir, "requirements-dir")
        os.mkdir(req_dir)

        # 5a. Subfile inside req_dir matching extension (should match line 310-314)
        sub_txt = os.path.join(req_dir, "base.txt")
        with open(sub_txt, "w") as f:
            f.write("content")

        # 5b. Subfile inside req_dir not matching extension (should be skipped)
        sub_other = os.path.join(req_dir, "other.md")
        with open(sub_other, "w") as f:
            f.write("content")

        # Call the cached method
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Normalize paths for comparison
        normalized_results = {os.path.normpath(p) for p in results}
        expected = {
            os.path.normpath(req_txt_file),
            os.path.normpath(req_in_file),
            os.path.normpath(sub_txt),
        }

        assert normalized_results == expected

        # Test lru_cache hit (calling again with same argument)
        results_cached = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert {os.path.normpath(p) for p in results_cached} == expected

    # Clean up cache state after test
    RequirementsFinder._get_files_from_dir_cached.cache_clear()
