# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create various files and directories to exercise all branches:
        # 1. File without "requirements" in name (should be ignored)
        ignored_file = os.path.join(tmpdir, "random.txt")
        with open(ignored_file, "w") as f:
            f.write("content")

        # 2. File with "requirements" in name but invalid extension (should be ignored)
        invalid_ext_file = os.path.join(tmpdir, "requirements.cfg")
        with open(invalid_ext_file, "w") as f:
            f.write("content")

        # 3. File with "requirements" in name and valid extension (.txt)
        req_file_txt = os.path.join(tmpdir, "requirements.txt")
        with open(req_file_txt, "w") as f:
            f.write("content")

        # 4. File with "requirements" in name and valid extension (.in)
        req_file_in = os.path.join(tmpdir, "requirements.in")
        with open(req_file_in, "w") as f:
            f.write("content")

        # 5. Directory with "requirements" in name containing valid and invalid subfiles
        req_dir = os.path.join(tmpdir, "requirements-dir")
        os.mkdir(req_dir)
        sub_valid = os.path.join(req_dir, "base.txt")
        with open(sub_valid, "w") as f:
            f.write("content")
        sub_invalid = os.path.join(req_dir, "other.py")
        with open(sub_invalid, "w") as f:
            f.write("content")

        # Clear cache to ensure fresh run
        RequirementsFinder._get_files_from_dir_cached.cache_clear()

        # Call the cached method
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Normalize paths for comparison
        resolved_results = {os.path.normpath(p) for p in results}
        expected = {
            os.path.normpath(req_file_txt),
            os.path.normpath(req_file_in),
            os.path.normpath(sub_valid),
        }

        assert expected.issubset(resolved_results)
        assert os.path.normpath(ignored_file) not in resolved_results
        assert os.path.normpath(invalid_ext_file) not in resolved_results
        assert os.path.normpath(sub_invalid) not in resolved_results

        # Test cache hit branch as well
        cached_results = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert cached_results == results

        RequirementsFinder._get_files_from_dir_cached.cache_clear()
