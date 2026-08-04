# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_paths():
    # Clear cache to ensure fresh execution
    RequirementsFinder._get_files_from_dir_cached.cache_clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Case 1: File/dir without "requirements" in name (should be skipped)
        ignored_file = os.path.join(tmpdir, "random.txt")
        with open(ignored_file, "w") as f:
            f.write("content")

        ignored_dir = os.path.join(tmpdir, "random_dir")
        os.makedirs(ignored_dir)

        # Case 2: A directory with "requirements" in its name containing valid and invalid extensions
        req_dir = os.path.join(tmpdir, "requirements_sub")
        os.makedirs(req_dir)
        sub_valid_txt = os.path.join(req_dir, "base.txt")
        sub_valid_in = os.path.join(req_dir, "dev.in")
        sub_invalid = os.path.join(req_dir, "other.py")
        for p in (sub_valid_txt, sub_valid_in, sub_invalid):
            with open(p, "w") as f:
                f.write("content")

        # Case 3: A file with "requirements" in its name with valid and invalid extensions
        req_file_txt = os.path.join(tmpdir, "requirements.txt")
        with open(req_file_txt, "w") as f:
            f.write("content")

        req_file_in = os.path.join(tmpdir, "test_requirements.in")
        with open(req_file_in, "w") as f:
            f.write("content")

        req_file_invalid = os.path.join(tmpdir, "requirements.py")
        with open(req_file_invalid, "w") as f:
            f.write("content")

        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Normalize paths for comparison across platforms
        normalized_results = {os.path.abspath(r) for r in results}

        expected = {
            os.path.abspath(sub_valid_txt),
            os.path.abspath(sub_valid_in),
            os.path.abspath(req_file_txt),
            os.path.abspath(req_file_in),
        }

        assert expected.issubset(normalized_results)
        assert os.path.abspath(sub_invalid) not in normalized_results
        assert os.path.abspath(req_file_invalid) not in normalized_results

    # Clean up cache
    RequirementsFinder._get_files_from_dir_cached.cache_clear()
