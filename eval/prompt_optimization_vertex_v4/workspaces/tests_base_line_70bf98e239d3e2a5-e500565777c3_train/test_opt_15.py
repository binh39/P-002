# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a file that does not match "requirements"
        other_file = os.path.join(tmpdir, "other.txt")
        with open(other_file, "w") as f:
            f.write("pytest\n")

        # Create a matching file (*requirements*.{txt,in})
        req_file = os.path.join(tmpdir, "requirements.txt")
        with open(req_file, "w") as f:
            f.write("requests\n")

        # Create a matching file with an extension not in exts, should be ignored
        req_invalid_ext = os.path.join(tmpdir, "requirements.cfg")
        with open(req_invalid_ext, "w") as f:
            f.write("foo\n")

        # Create a matching directory (*requirements*/*)
        req_dir = os.path.join(tmpdir, "requirements-dir")
        os.makedirs(req_dir, exist_ok=True)
        sub_file = os.path.join(req_dir, "dev.txt")
        with open(sub_file, "w") as f:
            f.write("pytest-cov\n")

        sub_invalid = os.path.join(req_dir, "dev.cfg")
        with open(sub_invalid, "w") as f:
            f.write("bar\n")

        # Clear cache to ensure execution
        RequirementsFinder._get_files_from_dir_cached.cache_clear()

        # Call the method covering lines 298-325
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Check results
        assert req_file in results
        assert sub_file in results
        assert other_file not in results
        assert req_invalid_ext not in results
        assert sub_invalid not in results

        # Test cache hit as well
        results_cached = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert results_cached == results

        RequirementsFinder._get_files_from_dir_cached.cache_clear()
