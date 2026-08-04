# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create various files and directories to exercise all branches in _get_files_from_dir_cached
        
        # 1. File without "requirements" in name (should be ignored)
        with open(os.path.join(tmpdir, "random_file.txt"), "w") as f:
            f.write("")

        # 2. File with "requirements" in name, matching extension (.txt)
        req_file_txt = os.path.join(tmpdir, "requirements.txt")
        with open(req_file_txt, "w") as f:
            f.write("")

        # 3. File with "requirements" in name, matching extension (.in)
        req_file_in = os.path.join(tmpdir, "requirements.in")
        with open(req_file_in, "w") as f:
            f.write("")

        # 4. File with "requirements" in name, but non-matching extension
        with open(os.path.join(tmpdir, "requirements.log"), "w") as f:
            f.write("")

        # 5. Directory with "requirements" in name, containing subfiles
        req_dir = os.path.join(tmpdir, "requirements_dir")
        os.mkdir(req_dir)
        
        sub_txt = os.path.join(req_dir, "base.txt")
        with open(sub_txt, "w") as f:
            f.write("")

        sub_in = os.path.join(req_dir, "dev.in")
        with open(sub_in, "w") as f:
            f.write("")

        sub_other = os.path.join(req_dir, "other.log")
        with open(sub_other, "w") as f:
            f.write("")

        # Clear cache to ensure fresh execution
        RequirementsFinder._get_files_from_dir_cached.cache_clear()

        # Call the method
        files = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Normalize paths for comparison/assertion
        normalized_files = {os.path.normpath(p) for p in files}
        expected = {
            os.path.normpath(req_file_txt),
            os.path.normpath(req_file_in),
            os.path.normpath(sub_txt),
            os.path.normpath(sub_in),
        }

        assert normalized_files == expected

        # Call again to exercise the lru_cache hit path
        cached_files = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert {os.path.normpath(p) for p in cached_files} == expected

        # Clean up cache state
        RequirementsFinder._get_files_from_dir_cached.cache_clear()
