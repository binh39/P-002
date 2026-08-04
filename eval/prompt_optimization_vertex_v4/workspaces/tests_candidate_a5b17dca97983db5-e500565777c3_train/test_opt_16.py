# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_files():
    # Clear cache to ensure fresh execution
    RequirementsFinder._get_files_from_dir_cached.cache_clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Case 1: Filename without "requirements" should be skipped (lines 304-305)
        with open(os.path.join(tmpdir, "random_file.txt"), "w") as f:
            f.write("pytest")

        # Case 2: File matching requirements with valid extension (lines 319-323)
        req_file_path = os.path.join(tmpdir, "requirements.txt")
        with open(req_file_path, "w") as f:
            f.write("pytest")

        # Case 3: File matching requirements with invalid extension (skipped inside loop)
        with open(os.path.join(tmpdir, "requirements.cfg"), "w") as f:
            f.write("pytest")

        # Case 4: Directory matching requirements (lines 309-316)
        sub_dir = os.path.join(tmpdir, "requirements_dir")
        os.mkdir(sub_dir)

        # Inside sub_dir: file ending with ext (lines 310-315)
        sub_file_valid = os.path.join(sub_dir, "dev.txt")
        with open(sub_file_valid, "w") as f:
            f.write("pytest")

        # Inside sub_dir: file not ending with ext
        sub_file_invalid = os.path.join(sub_dir, "dev.cfg")
        with open(sub_file_invalid, "w") as f:
            f.write("pytest")

        # Call the cached method
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Assertions
        assert req_file_path in results
        assert sub_file_valid in results
        assert not any("random_file" in r for r in results)
        assert not any("requirements.cfg" in r for r in results)
        assert not any("dev.cfg" in r for r in results)

        # Clean up cache
        RequirementsFinder._get_files_from_dir_cached.cache_clear()
