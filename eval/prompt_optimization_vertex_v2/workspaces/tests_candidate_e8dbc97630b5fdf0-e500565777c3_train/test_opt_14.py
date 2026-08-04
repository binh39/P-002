# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
import pytest
from isort.deprecated.finders import RequirementsFinder

def test_requirements_finder_cached_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Case 1: File containing "requirements" without valid extension (should be ignored)
        with open(os.path.join(tmpdir, "requirements_other.log"), "w") as f:
            f.write("")

        # Case 2: File containing "requirements" with valid extension (.txt)
        req_file_txt = os.path.join(tmpdir, "requirements.txt")
        with open(req_file_txt, "w") as f:
            f.write("")

        # Case 3: File containing "requirements" with valid extension (.in)
        req_file_in = os.path.join(tmpdir, "base_requirements.in")
        with open(req_file_in, "w") as f:
            f.write("")

        # Case 4: Directory containing "requirements"
        sub_dir = os.path.join(tmpdir, "requirements_dir")
        os.makedirs(sub_dir)
        
        # Subfile inside directory matching extension
        sub_txt = os.path.join(sub_dir, "prod.txt")
        with open(sub_txt, "w") as f:
            f.write("")

        # Subfile inside directory NOT matching extension
        sub_py = os.path.join(sub_dir, "prod.py")
        with open(sub_py, "w") as f:
            f.write("")

        # Clear cache to ensure execution
        RequirementsFinder._get_files_from_dir_cached.cache_clear()

        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Normalize paths for assertion comparison across OSes
        norm_results = {os.path.normpath(p) for p in results}
        expected = {
            os.path.normpath(req_file_txt),
            os.path.normpath(req_file_in),
            os.path.normpath(sub_txt),
        }

        assert expected.issubset(norm_results)
        assert os.path.normpath(sub_py) not in norm_results
        assert os.path.normpath(os.path.join(tmpdir, "requirements_other.log")) not in norm_results

        # Call again to exercise the lru_cache decorator path
        cached_results = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert set(cached_results) == set(results)

        RequirementsFinder._get_files_from_dir_cached.cache_clear()
