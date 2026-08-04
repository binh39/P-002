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
        # File without 'requirements' in name -> skipped by line 304 ('continue')
        ignored_file = os.path.join(tmpdir, "random.txt")
        with open(ignored_file, "w") as f:
            f.write("foo")

        # Directory with 'requirements' in name (lines 309-316)
        req_dir = os.path.join(tmpdir, "requirements_dir")
        os.mkdir(req_dir)
        
        # Subfile ending with valid extension (exts = ('.txt', '.in'))
        subfile_valid = os.path.join(req_dir, "base.txt")
        with open(subfile_valid, "w") as f:
            f.write("bar")

        # Subfile ending with invalid extension
        subfile_invalid = os.path.join(req_dir, "other.py")
        with open(subfile_invalid, "w") as f:
            f.write("baz")

        # File with 'requirements' in name and valid extension (lines 319-323)
        req_file_txt = os.path.join(tmpdir, "requirements.txt")
        with open(req_file_txt, "w") as f:
            f.write("qux")

        # File with 'requirements' in name but invalid extension
        req_file_invalid = os.path.join(tmpdir, "requirements.log")
        with open(req_file_invalid, "w") as f:
            f.write("quux")

        # Call the cached class method
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Assertions
        assert subfile_valid in results
        assert subfile_invalid not in results
        assert req_file_txt in results
        assert req_file_invalid not in results

        # Call again to exercise the cache hit path of lru_cache
        results_cached = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert results == results_cached

    # Cleanup cache
    RequirementsFinder._get_files_from_dir_cached.cache_clear()
