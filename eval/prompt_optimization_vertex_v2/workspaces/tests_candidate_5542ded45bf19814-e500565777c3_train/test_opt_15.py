# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create various files and directories to test different branches in _get_files_from_dir_cached
        
        # 1. File without "requirements" in name (should be skipped)
        other_file = os.path.join(tmpdir, "other.txt")
        with open(other_file, "w") as f:
            f.write("content")

        # 2. File with "requirements" in name matching extension (should be included)
        req_file = os.path.join(tmpdir, "requirements.txt")
        with open(req_file, "w") as f:
            f.write("content")

        # 3. File with "requirements" in name NOT matching extension (should not be included)
        req_invalid_ext = os.path.join(tmpdir, "requirements.cfg")
        with open(req_invalid_ext, "w") as f:
            f.write("content")

        # 4. Directory with "requirements" in name containing matching and non-matching files
        req_dir = os.path.join(tmpdir, "requirements_dir")
        os.makedirs(req_dir)
        sub_matching = os.path.join(req_dir, "base.txt")
        with open(sub_matching, "w") as f:
            f.write("content")
        sub_not_matching = os.path.join(req_dir, "base.cfg")
        with open(sub_not_matching, "w") as f:
            f.write("content")

        # Clear cache to ensure fresh run
        RequirementsFinder._get_files_from_dir_cached.cache_clear()

        # Call the method
        files = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Normalize paths for comparison
        resolved_files = {os.path.abspath(p) for p in files}
        expected_files = {os.path.abspath(req_file), os.path.abspath(sub_matching)}

        assert resolved_files == expected_files

        # Call again to test cache hit branch
        cached_files = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert {os.path.abspath(p) for p in cached_files} == expected_files

        # Clean up cache
        RequirementsFinder._get_files_from_dir_cached.cache_clear()
