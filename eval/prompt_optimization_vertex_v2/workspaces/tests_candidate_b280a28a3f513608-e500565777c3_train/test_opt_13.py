# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 321], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a file and directory matching the requirements finder logic
        # 1. A file matching *requirements*.{txt,in}
        req_file = os.path.join(tmpdir, "requirements.txt")
        with open(req_file, "w") as f:
            f.write("django\n")

        # 2. A non-matching file
        other_file = os.path.join(tmpdir, "readme.txt")
        with open(other_file, "w") as f:
            f.write("hello\n")

        # 3. A directory matching *requirements*/* containing valid extension files
        req_dir = os.path.join(tmpdir, "requirements_dir")
        os.mkdir(req_dir)
        sub_file = os.path.join(req_dir, "dev.in")
        with open(sub_file, "w") as f:
            f.write("pytest\n")

        # Clear cache to ensure clean execution of the cached method
        RequirementsFinder._get_files_from_dir_cached.cache_clear()

        # Call the method directly
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Assertions to ensure all branches (isdir, isfile, extensions check) are exercised
        assert req_file in results
        assert sub_file in results
        assert other_file not in results

        # Call it a second time to exercise the cached path return value as well
        results_cached = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert results_cached == results

        # Clean up cache
        RequirementsFinder._get_files_from_dir_cached.cache_clear()
