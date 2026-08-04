# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Case 1: File that does not contain "requirements" in name (should be skipped)
        ignored_file = os.path.join(tmpdir, "random.txt")
        with open(ignored_file, "w") as f:
            f.write("")

        # Case 2: File containing "requirements" and matching valid extension (e.g., .txt)
        req_file = os.path.join(tmpdir, "requirements.txt")
        with open(req_file, "w") as f:
            f.write("")

        # Case 3: File containing "requirements" but matching an invalid extension
        invalid_ext_file = os.path.join(tmpdir, "requirements.log")
        with open(invalid_ext_file, "w") as f:
            f.write("")

        # Case 4: Directory containing "requirements" with files inside matching extensions
        req_dir = os.path.join(tmpdir, "requirements_dir")
        os.makedirs(req_dir)
        sub_file_txt = os.path.join(req_dir, "base.txt")
        with open(sub_file_txt, "w") as f:
            f.write("")
        sub_file_in = os.path.join(req_dir, "dev.in")
        with open(sub_file_in, "w") as f:
            f.write("")
        sub_file_log = os.path.join(req_dir, "other.log")
        with open(sub_file_log, "w") as f:
            f.write("")

        # Clear cache to ensure clean execution of lines 298-325
        RequirementsFinder._get_files_from_dir_cached.cache_clear()

        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Assertions to ensure expected files are found and correctly filtered
        assert req_file in results
        assert os.path.join(req_dir, "base.txt") in results
        assert os.path.join(req_dir, "dev.in") in results
        assert ignored_file not in results
        assert invalid_ext_file not in results
        assert os.path.join(req_dir, "other.log") not in results

        # Clean up cache state after test
        RequirementsFinder._get_files_from_dir_cached.cache_clear()
