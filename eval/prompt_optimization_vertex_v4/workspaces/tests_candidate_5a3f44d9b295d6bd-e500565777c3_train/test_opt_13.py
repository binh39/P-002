# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a requirements file that matches file condition (*requirements*.{txt,in})
        req_file_txt = os.path.join(tmpdir, "requirements.txt")
        with open(req_file_txt, "w") as f:
            f.write("pytest\n")

        # Create a requirements file with non-matching extension
        req_file_other = os.path.join(tmpdir, "requirements.md")
        with open(req_file_other, "w") as f:
            f.write("pytest\n")

        # Create a non-matching file name
        other_file = os.path.join(tmpdir, "setup.txt")
        with open(other_file, "w") as f:
            f.write("setup\n")

        # Create a requirements directory matching directory condition (*requirements*/*)
        req_dir = os.path.join(tmpdir, "my_requirements_dir")
        os.makedirs(req_dir)
        sub_file_in = os.path.join(req_dir, "dev.in")
        with open(sub_file_in, "w") as f:
            f.write("black\n")
        sub_file_other = os.path.join(req_dir, "dev.md")
        with open(sub_file_other, "w") as f:
            f.write("black\n")

        # Clear cache to ensure fresh execution
        RequirementsFinder._get_files_from_dir_cached.cache_clear()

        # Call the cached method directly
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Assertions to ensure all branches (isdir, isfile, extensions matching, skipping non-matching) are exercised
        assert req_file_txt in results
        assert sub_file_in in results
        assert req_file_other not in results
        assert other_file not in results
        assert sub_file_other not in results

        # Clean up cache
        RequirementsFinder._get_files_from_dir_cached.cache_clear()
