# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a file that doesn't contain "requirements" (should be ignored)
        with open(os.path.join(tmpdir, "random.txt"), "w") as f:
            f.write("content")

        # Create a file matching *requirements*.{txt,in}
        req_file_txt = os.path.join(tmpdir, "requirements.txt")
        with open(req_file_txt, "w") as f:
            f.write("pkg")

        req_file_in = os.path.join(tmpdir, "dev-requirements.in")
        with open(req_file_in, "w") as f:
            f.write("pkg")

        # Create a directory matching *requirements*/* and files inside it
        req_dir = os.path.join(tmpdir, "requirements_dir")
        os.mkdir(req_dir)
        sub_file_txt = os.path.join(req_dir, "base.txt")
        with open(sub_file_txt, "w") as f:
            f.write("pkg")

        sub_file_other = os.path.join(req_dir, "ignore.dat")
        with open(sub_file_other, "w") as f:
            f.write("pkg")

        # Clear cache to ensure clean run
        RequirementsFinder._get_files_from_dir_cached.cache_clear()

        # Call the cached classmethod
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Normalize paths for comparison
        normalized_results = {os.path.normpath(p) for p in results}
        expected = {
            os.path.normpath(req_file_txt),
            os.path.normpath(req_file_in),
            os.path.normpath(sub_file_txt),
        }

        assert expected.issubset(normalized_results)
        assert os.path.normpath(os.path.join(req_dir, "ignore.dat")) not in normalized_results

        # Call again to exercise the cache hit path
        results_cached = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert results == results_cached

        # Cleanup cache
        RequirementsFinder._get_files_from_dir_cached.cache_clear()
