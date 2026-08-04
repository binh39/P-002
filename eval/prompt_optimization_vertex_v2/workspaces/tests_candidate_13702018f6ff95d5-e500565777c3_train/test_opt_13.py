# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. File that does not contain "requirements" in name (should be skipped)
        other_file = os.path.join(tmpdir, "other.txt")
        with open(other_file, "w") as f:
            f.write("package")

        # 2. File containing "requirements" matching extensions (should be included)
        req_file = os.path.join(tmpdir, "requirements.txt")
        with open(req_file, "w") as f:
            f.write("package")

        # 3. File containing "requirements" not matching extensions (should be skipped)
        req_invalid_ext = os.path.join(tmpdir, "requirements.log")
        with open(req_invalid_ext, "w") as f:
            f.write("package")

        # 4. Directory containing "requirements" with subfiles matching extensions (should be included)
        req_dir = os.path.join(tmpdir, "requirements_dir")
        os.makedirs(req_dir)
        sub_file_valid = os.path.join(req_dir, "base.txt")
        with open(sub_file_valid, "w") as f:
            f.write("package")
        sub_file_invalid = os.path.join(req_dir, "base.log")
        with open(sub_file_invalid, "w") as f:
            f.write("package")

        # Clear cache to ensure fresh run
        RequirementsFinder._get_files_from_dir_cached.cache_clear()

        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Normalize paths for comparison
        normalized_results = {os.path.normpath(p) for p in results}
        expected = {
            os.path.normpath(req_file),
            os.path.normpath(sub_file_valid),
        }

        assert expected.issubset(normalized_results)
        assert os.path.normpath(other_file) not in normalized_results
        assert os.path.normpath(req_invalid_ext) not in normalized_results
        assert os.path.normpath(sub_file_invalid) not in normalized_results

        # Test cached call hits the cache branch as well
        cached_results = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert set(cached_results) == set(results)

        RequirementsFinder._get_files_from_dir_cached.cache_clear()
