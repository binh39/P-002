# file: src\sample_repo\isort\isort\deprecated\finders.py:298-325
# asked: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 303], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}
# gained: {"lines": [298, 299, 300, 301, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 319, 320, 321, 322, 323, 325], "branches": [[303, 304], [303, 325], [304, 305], [304, 306], [309, 310], [309, 319], [310, 311], [310, 316], [319, 320], [320, 303], [320, 321], [321, 320], [321, 322]]}

import os
import tempfile
from isort.deprecated.finders import RequirementsFinder

def test_requirements_finder_cached():
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. File without "requirements" in name (should be skipped)
        with open(os.path.join(tmpdir, "random.txt"), "w") as f:
            f.write("")

        # 2. File with "requirements" in name but wrong extension (should be skipped)
        with open(os.path.join(tmpdir, "requirements.cfg"), "w") as f:
            f.write("")

        # 3. File with "requirements" in name and correct extension (.txt)
        req_txt = os.path.join(tmpdir, "requirements.txt")
        with open(req_txt, "w") as f:
            f.write("")

        # 4. File with "requirements" in name and correct extension (.in)
        req_in = os.path.join(tmpdir, "requirements-dev.in")
        with open(req_in, "w") as f:
            f.write("")

        # 5. Directory with "requirements" in name containing matching and non-matching files
        req_dir = os.path.join(tmpdir, "requirements_dir")
        os.mkdir(req_dir)
        sub_txt = os.path.join(req_dir, "prod.txt")
        with open(sub_txt, "w") as f:
            f.write("")
        sub_bad = os.path.join(req_dir, "prod.cfg")
        with open(sub_bad, "w") as f:
            f.write("")

        # Clear cache to ensure execution hits lines fresh
        RequirementsFinder._get_files_from_dir_cached.cache_clear()

        # Call the cached method
        results = RequirementsFinder._get_files_from_dir_cached(tmpdir)

        # Assertions
        assert req_txt in results
        assert req_in in results
        assert sub_txt in results
        assert sub_bad not in results

        # Test cache hit branch
        cached_results = RequirementsFinder._get_files_from_dir_cached(tmpdir)
        assert cached_results == results
