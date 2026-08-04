# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_files():
    # Clear cache before test to ensure clean state
    RequirementsFinder._get_files_from_dir_cached.cache_clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. File without "requirements" in name (should be skipped)
        other_file = os.path.join(tmpdir, "random.txt")
        with open(other_file, "w") as f:
            f.write("")

        # 2. File with "requirements" in name but wrong extension (should be skipped)
        wrong_ext_file = os.path.join(tmpdir, "requirements.cfg")
        with open(wrong_ext_file, "w") as f:
            f.write("")

        # 3. File with "requirements" in name and valid extension (.txt)
        req_txt_file = os.path.join(tmpdir, "requirements.txt")
        with open(req_txt_file, "w") as f:
            f.write("")

        # 4. File with "requirements" in name and valid extension (.in)
        req_in_file = os.path.join(tmpdir, "other_requirements.in")
        with open(req_in_file, "w") as f:
            f.write("")

        # 5. Directory with "requirements" in name, containing valid and invalid subfiles
        req_dir = os.path.join(tmpdir, "requirements_dir")
        os.makedirs(req_dir)

        sub_valid = os.path.join(req_dir, "dev.txt")
        with open(sub_valid, "w") as f:
            f.write("")

        sub_invalid = os.path.join(req_dir, "dev.cfg")
        with open(sub_invalid, "w") as f:
            f.write("")

        # Call the cached method directly to cover lines 298-325 and all branches
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Normalize paths for comparison across platforms
        normalized_results = {os.path.normpath(p) for p in results}
        expected = {
            os.path.normpath(req_txt_file),
            os.path.normpath(req_in_file),
            os.path.normpath(sub_valid),
        }

        assert normalized_results == expected

    # Clear cache again after test
    RequirementsFinder._get_files_from_dir_cached.cache_clear()
