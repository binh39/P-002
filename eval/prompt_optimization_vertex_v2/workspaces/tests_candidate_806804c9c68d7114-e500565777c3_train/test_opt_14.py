# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_files():
    # Clear the lru_cache for a clean test state
    RequirementsFinder._get_files_from_dir_cached.cache_clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. File without "requirements" in name (should be skipped)
        ignored_file = os.path.join(tmpdir, "random.txt")
        with open(ignored_file, "w") as f:
            f.write("pytest")

        # 2. File with "requirements" in name but wrong extension (should be skipped by is_file check or extension check)
        wrong_ext_file = os.path.join(tmpdir, "requirements.cfg")
        with open(wrong_ext_file, "w") as f:
            f.write("pytest")

        # 3. File with "requirements" in name and valid extension (.txt)
        req_txt_file = os.path.join(tmpdir, "requirements.txt")
        with open(req_txt_file, "w") as f:
            f.write("pytest")

        # 4. File with "requirements" in name and valid extension (.in)
        req_in_file = os.path.join(tmpdir, "dev-requirements.in")
        with open(req_in_file, "w") as f:
            f.write("pytest")

        # 5. Directory with "requirements" in name containing subfiles (valid and invalid)
        req_dir = os.path.join(tmpdir, "requirements-dir")
        os.mkdir(req_dir)

        sub_valid_txt = os.path.join(req_dir, "base.txt")
        with open(sub_valid_txt, "w") as f:
            f.write("pytest")

        sub_invalid_ext = os.path.join(tmpdir, "requirements-dir", "base.cfg")
        with open(sub_invalid_ext, "w") as f:
            f.write("pytest")

        sub_valid_in = os.path.join(req_dir, "extra.in")
        with open(sub_valid_in, "w") as f:
            f.write("pytest")

        # Execute the method
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Assertions
        # Should include req_txt_file, req_in_file, sub_valid_txt, sub_valid_in
        # Should NOT include ignored_file, wrong_ext_file, sub_invalid_ext
        assert req_txt_file in results
        assert req_in_file in results
        assert sub_valid_txt in results
        assert sub_valid_in in results

        assert ignored_file not in results
        assert wrong_ext_file not in results
        assert sub_invalid_ext not in results

        # Test cache hit (calling again covers cached path)
        results_cached = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert results_cached == results

    # Cleanup cache
    RequirementsFinder._get_files_from_dir_cached.cache_clear()
