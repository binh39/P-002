# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_files():
    # Clear cache to start fresh
    RequirementsFinder._get_files_from_dir_cached.cache_clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Case 1: File that does not contain "requirements" (should be ignored)
        with open(os.path.join(tmpdir, "random.txt"), "w") as f:
            f.write("content")

        # Case 2: File containing "requirements" but invalid extension (should be ignored)
        with open(os.path.join(tmpdir, "requirements.cfg"), "w") as f:
            f.write("content")

        # Case 3: File containing "requirements" with valid extension (.txt)
        req_txt_path = os.path.join(tmpdir, "requirements.txt")
        with open(req_txt_path, "w") as f:
            f.write("content")

        # Case 4: File containing "requirements" with valid extension (.in)
        req_in_path = os.path.join(tmpdir, "requirements.in")
        with open(req_in_path, "w") as f:
            f.write("content")

        # Case 5: Directory containing "requirements"
        sub_dir_path = os.path.join(tmpdir, "requirements_dir")
        os.mkdir(sub_dir_path)

        # Inside sub_dir_path: file without valid extension
        with open(os.path.join(sub_dir_path, "sub_random.cfg"), "w") as f:
            f.write("content")

        # Inside sub_dir_path: file with valid extension (.txt)
        sub_txt_path = os.path.join(sub_dir_path, "dev.txt")
        with open(sub_txt_path, "w") as f:
            f.write("content")

        # Inside sub_dir_path: file with valid extension (.in)
        sub_in_path = os.path.join(sub_dir_path, "prod.in")
        with open(sub_in_path, "w") as f:
            f.write("content")

        # Call the method
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Normalize paths for comparison
        results_set = {os.path.abspath(p) for p in results}
        expected_set = {
            os.path.abspath(req_txt_path),
            os.path.abspath(req_in_path),
            os.path.abspath(sub_txt_path),
            os.path.abspath(sub_in_path),
        }

        assert results_set == expected_set

        # Also test the cached branch by calling it a second time
        cached_results = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert {os.path.abspath(p) for p in cached_results} == expected_set

    # Clear cache after test
    RequirementsFinder._get_files_from_dir_cached.cache_clear()
