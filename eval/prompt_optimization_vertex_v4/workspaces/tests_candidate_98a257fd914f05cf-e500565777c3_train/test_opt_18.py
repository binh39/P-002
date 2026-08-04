# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder

def test_requirements_finder_cached_files():
    # Clear the lru_cache to ensure we exercise the method cleanly
    RequirementsFinder._get_files_from_dir_cached.cache_clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Case 1: File that doesn't contain "requirements" (should be skipped)
        other_file = os.path.join(tmpdir, "random.txt")
        with open(other_file, "w") as f:
            f.write("test")

        # Case 2: File containing "requirements" matching an extension (.txt)
        req_file = os.path.join(tmpdir, "requirements.txt")
        with open(req_file, "w") as f:
            f.write("pkg==1.0")

        # Case 3: File containing "requirements" NOT matching an extension (should not be added)
        req_bad_ext = os.path.join(tmpdir, "requirements.log")
        with open(req_bad_ext, "w") as f:
            f.write("pkg==1.0")

        # Case 4: Directory containing "requirements" (e.g. requirements/subfile.in)
        req_dir = os.path.join(tmpdir, "requirements_dir")
        os.makedirs(req_dir)
        sub_file_in = os.path.join(req_dir, "dev.in")
        with open(sub_file_in, "w") as f:
            f.write("pytest")

        sub_file_txt = os.path.join(req_dir, "prod.txt")
        with open(sub_file_txt, "w") as f:
            f.write("gunicorn")

        sub_file_other = os.path.join(req_dir, "other.cfg")
        with open(sub_file_other, "w") as f:
            f.write("config")

        # Call the cached method
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Normalize paths for platform-independent assertion
        norm_results = {os.path.normpath(p) for p in results}
        expected = {
            os.path.normpath(req_file),
            os.path.normpath(sub_file_in),
            os.path.normpath(sub_file_txt),
        }

        assert expected.issubset(norm_results)
        assert os.path.normpath(other_file) not in norm_results
        assert os.path.normpath(req_bad_ext) not in norm_results
        assert os.path.normpath(sub_file_other) not in norm_results

    # Clean up cache
    RequirementsFinder._get_files_from_dir_cached.cache_clear()
