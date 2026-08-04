# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_files():
    # Clear cache to ensure clean test state
    RequirementsFinder._get_files_from_dir_cached.cache_clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. File without "requirements" in name (should be skipped)
        ignored_file = os.path.join(tmpdir, "random.txt")
        with open(ignored_file, "w") as f:
            f.write("pytest")

        # 2. File with "requirements" in name but wrong extension (should be skipped)
        wrong_ext_file = os.path.join(tmpdir, "requirements.cfg")
        with open(wrong_ext_file, "w") as f:
            f.write("pytest")

        # 3. File matching requirements and valid extension (.txt)
        req_txt_file = os.path.join(tmpdir, "requirements.txt")
        with open(req_txt_file, "w") as f:
            f.write("pytest")

        # 4. File matching requirements and valid extension (.in)
        req_in_file = os.path.join(tmpdir, "prod-requirements.in")
        with open(req_in_file, "w") as f:
            f.write("pytest")

        # 5. Directory matching requirements containing valid subfiles
        req_dir = os.path.join(tmpdir, "requirements-dev")
        os.makedirs(req_dir)
        sub_txt = os.path.join(req_dir, "base.txt")
        with open(sub_txt, "w") as f:
            f.write("pytest")

        sub_in = os.path.join(req_dir, "other.in")
        with open(sub_in, "w") as f:
            f.write("pytest")

        sub_ignored = os.path.join(req_dir, "ignore.cfg")
        with open(sub_ignored, "w") as f:
            f.write("pytest")

        # Call the method under test
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Normalize paths for comparison
        normalized_results = {os.path.normpath(p) for p in results}
        expected = {
            os.path.normpath(req_txt_file),
            os.path.normpath(req_in_file),
            os.path.normpath(sub_txt),
            os.path.normpath(sub_in),
        }

        assert expected.issubset(normalized_results)
        assert os.path.normpath(ignored_file) not in normalized_results
        assert os.path.normpath(wrong_ext_file) not in normalized_results
        assert os.path.normpath(sub_ignored) not in normalized_results

        # Test lru_cache hits by calling it again
        cached_results = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert cached_results == results

    # Clear cache again for cleanup
    RequirementsFinder._get_files_from_dir_cached.cache_clear()
