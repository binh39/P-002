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
        other_file = os.path.join(tmpdir, "random.txt")
        with open(other_file, "w") as f:
            f.write("pytest")

        # 2. Directory containing "requirements" with valid extension subfile
        req_dir = os.path.join(tmpdir, "requirements_dir")
        os.makedirs(req_dir)
        sub_txt = os.path.join(req_dir, "base.txt")
        with open(sub_txt, "w") as f:
            f.write("pkg1")
        sub_invalid = os.path.join(req_dir, "base.md")
        with open(sub_invalid, "w") as f:
            f.write("pkg2")

        # 3. File containing "requirements" with valid extension (.txt and .in)
        req_file_txt = os.path.join(tmpdir, "requirements.txt")
        with open(req_file_txt, "w") as f:
            f.write("pkg3")

        req_file_in = os.path.join(tmpdir, "dev-requirements.in")
        with open(req_file_in, "w") as f:
            f.write("pkg4")

        # 4. File containing "requirements" but with invalid extension
        req_file_invalid = os.path.join(tmpdir, "requirements.doc")
        with open(req_file_invalid, "w") as f:
            f.write("pkg5")

        # Clear cache to ensure clean run
        RequirementsFinder._get_files_from_dir_cached.cache_clear()

        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Normalize paths for comparison across platforms
        results_normalized = {os.path.normpath(p) for p in results}
        expected = {
            os.path.normpath(sub_txt),
            os.path.normpath(req_file_txt),
            os.path.normpath(req_file_in),
        }

        assert expected.issubset(results_normalized)
        assert os.path.normpath(other_file) not in results_normalized
        assert os.path.normpath(req_file_invalid) not in results_normalized
        assert os.path.normpath(sub_invalid) not in results_normalized

        # Test cache hit branch
        cached_results = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert cached_results == results

        # Clean up cache
        RequirementsFinder._get_files_from_dir_cached.cache_clear()
