# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a file that doesn't match 'requirements'
        with open(os.path.join(tmpdir, "other.txt"), "w") as f:
            f.write("content")

        # Create a file matching '*requirements*.txt'
        req_file = os.path.join(tmpdir, "requirements.txt")
        with open(req_file, "w") as f:
            f.write("content")

        # Create a file matching '*requirements*.in'
        req_in = os.path.join(tmpdir, "dev-requirements.in")
        with open(req_in, "w") as f:
            f.write("content")

        # Create a directory matching '*requirements*' containing valid extension files
        req_dir = os.path.join(tmpdir, "requirements_dir")
        os.makedirs(req_dir)
        sub_file = os.path.join(req_dir, "base.txt")
        with open(sub_file, "w") as f:
            f.write("content")
        
        # Create a subdirectory file with invalid extension
        sub_invalid = os.path.join(req_dir, "ignore.md")
        with open(sub_invalid, "w") as f:
            f.write("content")

        # Clear cache to ensure execution
        RequirementsFinder._get_files_from_dir_cached.cache_clear()

        # Call the cached method
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Assertions
        assert req_file in results
        assert req_in in results
        assert sub_file in results
        assert sub_invalid not in results
        assert not any("other.txt" in r for r in results)

        # Call again to test cache hit/return path
        results_cached = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert set(results) == set(results_cached)

        # Clean up cache state
        RequirementsFinder._get_files_from_dir_cached.cache_clear()
