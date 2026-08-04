# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_paths():
    # Clear cache to ensure fresh execution of _get_files_from_dir_cached
    RequirementsFinder._get_files_from_dir_cached.cache_clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. File not containing "requirements" -> should be skipped (line 304)
        non_req_file = os.path.join(tmpdir, "random.txt")
        with open(non_req_file, "w") as f:
            f.write("pytest")

        # 2. File containing "requirements" but not matching exts (.txt, .in) -> should be skipped by file check
        req_wrong_ext = os.path.join(tmpdir, "requirements.cfg")
        with open(req_wrong_ext, "w") as f:
            f.write("pytest")

        # 3. File containing "requirements" and matching .txt -> should be added (lines 319-323)
        req_txt_file = os.path.join(tmpdir, "requirements.txt")
        with open(req_txt_file, "w") as f:
            f.write("pytest")

        # 4. File containing "requirements" and matching .in -> should be added
        req_in_file = os.path.join(tmpdir, "requirements-dev.in")
        with open(req_in_file, "w") as f:
            f.write("pytest")

        # 5. Directory containing "requirements" (lines 309-316)
        req_dir = os.path.join(tmpdir, "requirements-dir")
        os.makedirs(req_dir)

        # Subfile inside req_dir that matches exts
        subfile_match = os.path.join(req_dir, "base.txt")
        with open(subfile_match, "w") as f:
            f.write("pytest")

        # Subfile inside req_dir that does not match exts
        subfile_nomatch = os.path.join(req_dir, "base.cfg")
        with open(subfile_nomatch, "w") as f:
            f.write("pytest")

        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Verify that expected files are present and unwanted ones are absent
        assert os.path.normpath(req_txt_file) in [os.path.normpath(p) for p in results]
        assert os.path.normpath(req_in_file) in [os.path.normpath(p) for p in results]
        assert os.path.normpath(subfile_match) in [os.path.normpath(p) for p in results]
        assert os.path.normpath(non_req_file) not in [os.path.normpath(p) for p in results]
        assert os.path.normpath(req_wrong_ext) not in [os.path.normpath(p) for p in results]
        assert os.path.normpath(subfile_nomatch) not in [os.path.normpath(p) for p in results]

    # Clean up cache
    RequirementsFinder._get_files_from_dir_cached.cache_clear()
