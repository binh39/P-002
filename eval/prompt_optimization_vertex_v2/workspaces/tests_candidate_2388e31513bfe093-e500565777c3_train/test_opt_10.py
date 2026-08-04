# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_files():
    # Clear the lru_cache for clean test state
    RequirementsFinder._get_files_from_dir_cached.cache_clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create various files and directories to test all branches:
        # 1. File without "requirements" in name (should be skipped)
        # 2. File with "requirements" in name, but not matching exts (should be checked by isfile and not matched)
        # 3. File with "requirements" in name and matching exts (should be included)
        # 4. Directory without "requirements" in name (should be skipped)
        # 5. Directory with "requirements" in name:
        #    - contains subfile matching exts (should be included)
        #    - contains subfile not matching exts (should be skipped)

        # 1. Non-matching file
        with open(os.path.join(tmpdir, "random_file.txt"), "w") as f:
            f.write("")

        # 2. Requirements file with non-matching extension
        with open(os.path.join(tmpdir, "requirements.cfg"), "w") as f:
            f.write("")

        # 3. Requirements file with matching extension (.txt and .in)
        req_txt = os.path.join(tmpdir, "requirements.txt")
        with open(req_txt, "w") as f:
            f.write("")

        req_in = os.path.join(tmpdir, "prod-requirements.in")
        with open(req_in, "w") as f:
            f.write("")

        # 4. Non-matching directory
        non_match_dir = os.path.join(tmpdir, "other_dir")
        os.mkdir(non_match_dir)
        with open(os.path.join(non_match_dir, "sub.txt"), "w") as f:
            f.write("")

        # 5. Requirements directory
        req_dir = os.path.join(tmpdir, "requirements_dir")
        os.mkdir(req_dir)
        
        sub_match = os.path.join(req_dir, "base.txt")
        with open(sub_match, "w") as f:
            f.write("")

        sub_no_match = os.path.join(req_dir, "other.cfg")
        with open(sub_no_match, "w") as f:
            f.write("")

        sub_in = os.path.join(req_dir, "dev.in")
        with open(sub_in, "w") as f:
            f.write("")

        # Call the method
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Normalize paths for platform independence
        normalized_results = {os.path.normpath(p) for p in results}
        expected = {
            os.path.normpath(req_txt),
            os.path.normpath(req_in),
            os.path.normpath(sub_match),
            os.path.normpath(sub_in),
        }

        assert normalized_results == expected

        # Test lru_cache hit path
        cached_results = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert {os.path.normpath(p) for p in cached_results} == expected

    # Clean up cache
    RequirementsFinder._get_files_from_dir_cached.cache_clear()
