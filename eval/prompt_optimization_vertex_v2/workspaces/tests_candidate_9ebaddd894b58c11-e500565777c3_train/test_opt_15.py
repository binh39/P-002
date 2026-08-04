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
            f.write("")

        # 2. File matching requirements but with wrong extension (should not be added)
        wrong_ext = os.path.join(tmpdir, "requirements.cfg")
        with open(wrong_ext, "w") as f:
            f.write("")

        # 3. File matching requirements with valid extension (.txt) -> lines 319-323
        req_file_txt = os.path.join(tmpdir, "requirements.txt")
        with open(req_file_txt, "w") as f:
            f.write("")

        # 4. File matching requirements with valid extension (.in) -> lines 319-323
        req_file_in = os.path.join(tmpdir, "requirements.in")
        with open(req_file_in, "w") as f:
            f.write("")

        # 5. Directory matching requirements containing files -> lines 309-315
        req_dir = os.path.join(tmpdir, "requirements-folder")
        os.mkdir(req_dir)
        sub_valid = os.path.join(req_dir, "base.txt")
        with open(sub_valid, "w") as f:
            f.write("")
        sub_invalid = os.path.join(req_dir, "base.cfg")
        with open(sub_invalid, "w") as f:
            f.write("")

        # Clear cache to ensure execution goes through the method body
        RequirementsFinder._get_files_from_dir_cached.cache_clear()

        # Call the cached class method
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Assertions
        assert req_file_txt in results
        assert req_file_in in results
        assert sub_valid in results
        assert other_file not in results
        assert wrong_ext not in results
        assert sub_invalid not in results

        # Clean up cache
        RequirementsFinder._get_files_from_dir_cached.cache_clear()
