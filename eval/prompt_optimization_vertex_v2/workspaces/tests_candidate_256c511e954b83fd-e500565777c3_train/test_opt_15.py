# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_files():
    # Clear cache to ensure fresh execution
    RequirementsFinder._get_files_from_dir_cached.cache_clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Case 1: File/dir without "requirements" in name (should be skipped)
        ignored_file = os.path.join(tmpdir, "random.txt")
        with open(ignored_file, "w") as f:
            f.write("content")

        ignored_dir = os.path.join(tmpdir, "random_dir")
        os.makedirs(ignored_dir)

        # Case 2: Directory with "requirements" in name containing matching and non-matching subfiles
        req_dir = os.path.join(tmpdir, "requirements-dev")
        os.makedirs(req_dir)
        subfile_match = os.path.join(req_dir, "base.txt")
        with open(subfile_match, "w") as f:
            f.write("pytest")
        subfile_nomatch = os.path.join(req_dir, "base.py")
        with open(subfile_nomatch, "w") as f:
            f.write("import os")

        # Case 3: File with "requirements" in name and valid extension
        req_file_txt = os.path.join(tmpdir, "requirements.txt")
        with open(req_file_txt, "w") as f:
            f.write("isort")

        # Case 4: File with "requirements" in name and invalid extension
        req_file_py = os.path.join(tmpdir, "requirements.py")
        with open(req_file_py, "w") as f:
            f.write("pass")

        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Normalize paths for platform independence
        normalized_results = {os.path.normpath(p) for p in results}
        expected = {
            os.path.normpath(subfile_match),
            os.path.normpath(req_file_txt),
        }

        assert expected.issubset(normalized_results)
        # Ensure non-matching subfiles or files are not included
        assert os.path.normpath(subfile_nomatch) not in normalized_results
        assert os.path.normpath(req_file_py) not in normalized_results

    # Clean up cache
    RequirementsFinder._get_files_from_dir_cached.cache_clear()
