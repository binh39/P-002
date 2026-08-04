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
        
        # 1. File without "requirements" in name (should be skipped)
        ignored_file = os.path.join(tmpdir, "random.txt")
        with open(ignored_file, "w") as f:
            f.write("")

        # 2. File with "requirements" in name matching an extension (.txt)
        req_file_txt = os.path.join(tmpdir, "requirements.txt")
        with open(req_file_txt, "w") as f:
            f.write("")

        # 3. File with "requirements" in name matching another extension (.in)
        req_file_in = os.path.join(tmpdir, "requirements.in")
        with open(req_file_in, "w") as f:
            f.write("")

        # 4. File with "requirements" in name but non-matching extension
        req_file_other = os.path.join(tmpdir, "requirements.cfg")
        with open(req_file_other, "w") as f:
            f.write("")

        # 5. Directory containing "requirements" with subfiles (matching and non-matching extensions)
        req_dir = os.path.join(tmpdir, "requirements_dir")
        os.makedirs(req_dir)
        
        sub_txt = os.path.join(req_dir, "base.txt")
        with open(sub_txt, "w") as f:
            f.write("")

        sub_in = os.path.join(req_dir, "dev.in")
        with open(sub_in, "w") as f:
            f.write("")

        sub_other = os.path.join(req_dir, "other.cfg")
        with open(sub_other, "w") as f:
            f.write("")

        # Clear cache to ensure fresh execution
        RequirementsFinder._get_files_from_dir_cached.cache_clear()

        # Call the cached method directly
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Normalize paths for platform-agnostic comparison
        normalized_results = {os.path.normpath(p) for p in results}
        expected = {
            os.path.normpath(req_file_txt),
            os.path.normpath(req_file_in),
            os.path.normpath(sub_txt),
            os.path.normpath(sub_in),
        }

        assert expected.issubset(normalized_results)
        assert os.path.normpath(ignored_file) not in normalized_results
        assert os.path.normpath(req_file_other) not in normalized_results
        assert os.path.normpath(sub_other) not in normalized_results

        # Call a second time to hit the lru_cache hit branch
        results_cached = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert results == results_cached

        # Clean up cache state
        RequirementsFinder._get_files_from_dir_cached.cache_clear()
