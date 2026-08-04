# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder


def test_requirements_finder_cached_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a file that doesn't contain "requirements"
        with open(os.path.join(tmpdir, "random.txt"), "w") as f:
            f.write("")

        # Create a matching file that is not a requirements file (e.g., wrong extension)
        with open(os.path.join(tmpdir, "requirements.log"), "w") as f:
            f.write("")

        # Create a matching file (*requirements*.{txt,in}) that is a file
        req_file_txt = os.path.join(tmpdir, "requirements.txt")
        with open(req_file_txt, "w") as f:
            f.write("")

        req_file_in = os.path.join(tmpdir, "dev-requirements.in")
        with open(req_file_in, "w") as f:
            f.write("")

        # Create a matching directory (*requirements*/*.{txt,in})
        sub_dir = os.path.join(tmpdir, "requirements_dir")
        os.mkdir(sub_dir)

        # File inside subdirectory matching ext
        sub_file_txt = os.path.join(sub_dir, "prod.txt")
        with open(sub_file_txt, "w") as f:
            f.write("")

        # File inside subdirectory not matching ext
        sub_file_png = os.path.join(sub_dir, "prod.png")
        with open(sub_file_png, "w") as f:
            f.write("")

        # Clear cache to ensure execution
        RequirementsFinder._get_files_from_dir_cached.cache_clear()

        # Call the cached classmethod directly to cover lines 298-325
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        assert req_file_txt in results
        assert req_file_in in results
        assert sub_file_txt in results
        assert sub_file_png not in results

        # Test cache hit (calling again with same path)
        results_cached = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert set(results) == set(results_cached)

        RequirementsFinder._get_files_from_dir_cached.cache_clear()
