# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create various files and subdirectories to cover all branches in _get_files_from_dir_cached
        # 1. File without "requirements" in name (should be skipped)
        other_file = os.path.join(tmpdir, "random.txt")
        with open(other_file, "w") as f:
            f.write("content")

        # 2. File with "requirements" in name but invalid extension (should not match exts)
        invalid_ext_file = os.path.join(tmpdir, "requirements.cfg")
        with open(invalid_ext_file, "w") as f:
            f.write("content")

        # 3. File with "requirements" in name and valid extension (.txt)
        valid_txt_file = os.path.join(tmpdir, "requirements.txt")
        with open(valid_txt_file, "w") as f:
            f.write("content")

        # 4. File with "requirements" in name and valid extension (.in)
        valid_in_file = os.path.join(tmpdir, "requirements.in")
        with open(valid_in_file, "w") as f:
            f.write("content")

        # 5. Directory with "requirements" in name containing subfiles
        req_dir = os.path.join(tmpdir, "requirements_dir")
        os.makedirs(req_dir)
        
        sub_valid_txt = os.path.join(req_dir, "base.txt")
        with open(sub_valid_txt, "w") as f:
            f.write("content")

        sub_invalid_ext = os.path.join(req_dir, "base.cfg")
        with open(sub_invalid_ext, "w") as f:
            f.write("content")

        # Clear cache before testing to ensure clean execution
        RequirementsFinder._get_files_from_dir_cached.cache_clear()

        # Call the cached method
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Assertions
        assert valid_txt_file in results
        assert valid_in_file in results
        assert sub_valid_txt in results
        assert other_file not in results
        assert invalid_ext_file not in results
        assert sub_invalid_ext not in results

        # Test cache hit by calling again
        cached_results = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert sorted(cached_results) == sorted(results)

        # Clean up cache
        RequirementsFinder._get_files_from_dir_cached.cache_clear()
