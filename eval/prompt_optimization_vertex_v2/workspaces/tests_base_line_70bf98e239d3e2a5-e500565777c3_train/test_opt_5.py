# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a file that does not match requirements
        other_file = os.path.join(tmpdir, "setup.py")
        with open(other_file, "w") as f:
            f.write("# setup")

        # Create a matching file (*requirements*.{txt,in})
        req_file = os.path.join(tmpdir, "requirements.txt")
        with open(req_file, "w") as f:
            f.write("pytest")

        # Create a non-matching extension for requirements file
        req_invalid_ext = os.path.join(tmpdir, "requirements.md")
        with open(req_invalid_ext, "w") as f:
            f.write("pytest")

        # Create a matching directory (*requirements*/*)
        req_dir = os.path.join(tmpdir, "dev-requirements")
        os.makedirs(req_dir)
        sub_txt = os.path.join(req_dir, "test.txt")
        with open(sub_txt, "w") as f:
            f.write("tox")

        sub_md = os.path.join(req_dir, "readme.md")
        with open(sub_md, "w") as f:
            f.write("readme")

        # Clear cache before testing to ensure execution
        RequirementsFinder._get_files_from_dir_cached.cache_clear()

        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Assertions
        assert req_file in results
        assert sub_txt in results
        assert other_file not in results
        assert req_invalid_ext not in results
        assert sub_md not in results

        # Test cache hit coverage as well
        results_cached = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert sorted(results) == sorted(results_cached)

        # Cleanup cache
        RequirementsFinder._get_files_from_dir_cached.cache_clear()
