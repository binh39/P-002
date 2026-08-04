# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create various files and subdirectories to test all branches in _get_files_from_dir_cached
        
        # 1. File not containing "requirements" -> should be ignored
        other_file = os.path.join(tmpdir, "setup.py")
        with open(other_file, "w") as f:
            f.write("print()")

        # 2. File containing "requirements" but wrong extension -> should not be added via file check
        wrong_ext_file = os.path.join(tmpdir, "requirements.cfg")
        with open(wrong_ext_file, "w") as f:
            f.write("pytest")

        # 3. File containing "requirements" with valid extension (.txt) -> os.path.isfile branch
        req_txt_file = os.path.join(tmpdir, "requirements.txt")
        with open(req_txt_file, "w") as f:
            f.write("click")

        # 4. File containing "requirements" with valid extension (.in) -> os.path.isfile branch
        req_in_file = os.path.join(tmpdir, "requirements.in")
        with open(req_in_file, "w") as f:
            f.write("black")

        # 5. Directory containing "requirements" -> os.path.isdir branch
        req_dir = os.path.join(tmpdir, "requirements-dev")
        os.makedirs(req_dir)

        # Inside req_dir: subfile with valid extension (.txt)
        sub_txt = os.path.join(req_dir, "test.txt")
        with open(sub_txt, "w") as f:
            f.write("pytest")

        # Inside req_dir: subfile with invalid extension (.cfg)
        sub_cfg = os.path.join(req_dir, "test.cfg")
        with open(sub_cfg, "w") as f:
            f.write("other")

        # Call the cached method directly to cover lines 298-325 and all branches
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Normalize paths for platform-independent assertion
        normalized_results = {os.path.normpath(p) for p in results}

        expected = {
            os.path.normpath(req_txt_file),
            os.path.normpath(req_in_file),
            os.path.normpath(sub_txt),
        }

        assert normalized_results == expected

        # Call again to exercise the cache hit path as well
        cached_results = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert {os.path.normpath(p) for p in cached_results} == expected

    # Clear cache to clean up state
    RequirementsFinder._get_files_from_dir_cached.cache_clear()
