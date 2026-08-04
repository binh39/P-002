# file: src\sample_repo\isort\isort\main.py:975-1058
# asked: {"lines": [975, 976, 977, 978, 979, 982, 983, 985, 986, 987, 988, 989, 992, 993, 994, 995, 996, 997, 1000, 1001, 1002, 1003, 1004, 1005, 1007, 1008, 1009, 1010, 1012, 1013, 1015, 1016, 1017, 1018, 1020, 1021, 1023, 1024, 1025, 1026, 1028, 1029, 1032, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1043, 1044, 1045, 1046, 1047, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1058], "branches": [[1035, 1036], [1035, 1043], [1050, 0], [1050, 1051], [1051, 1052], [1051, 1053], [1053, 1054], [1053, 1055], [1055, 1056], [1055, 1058]]}
# gained: {"lines": [975, 976, 977, 978, 979, 982, 983, 985, 986, 987, 988, 989, 992, 993, 994, 995, 996, 997, 1000, 1001, 1002, 1003, 1004, 1005, 1007, 1008, 1009, 1010, 1012, 1013, 1015, 1016, 1017, 1018, 1020, 1021, 1023, 1024, 1025, 1026, 1028, 1029, 1032, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1043, 1044, 1045, 1046, 1047, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1058], "branches": [[1035, 1036], [1035, 1043], [1050, 0], [1050, 1051], [1051, 1052], [1051, 1053], [1053, 1054], [1053, 1055], [1055, 1056], [1055, 1058]]}

import io
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
from isort.main import identify_imports_main
from isort import api

def test_identify_imports_main_stdin(capsys):
    stream = io.StringIO("import os\nimport sys\n")
    # Test with "-" for stdin stream reading
    identify_imports_main(argv=["-"], stdin=stream)
    captured = capsys.readouterr()
    assert "os" in captured.out

def test_identify_imports_main_paths_and_unique_options(capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "sample.py"
        p.write_text("import os.path\nimport sys\nfrom collections import defaultdict\n")

        # 1. Default unique (else branch)
        identify_imports_main(argv=[str(p)])
        captured = capsys.readouterr()
        assert "os" in captured.out

        # 2. --packages (ImportKey.PACKAGE)
        identify_imports_main(argv=["--packages", str(p)])
        captured = capsys.readouterr()
        assert "os" in captured.out

        # 3. --modules (ImportKey.MODULE)
        identify_imports_main(argv=["--modules", str(p)])
        captured = capsys.readouterr()
        assert "os" in captured.out

        # 4. --attributes (ImportKey.ATTRIBUTE)
        identify_imports_main(argv=["--attributes", str(p)])
        captured = capsys.readouterr()
        # attributes branch prints module.attribute or similar if found, or iterates.
        # Even if empty/non-empty, it exercises lines 1055-1056.

        # 5. --unique (boolean True, goes to else branch)
        identify_imports_main(argv=["--unique", str(p), "--top-only", "--follow-links"])
        captured = capsys.readouterr()
        assert "os" in captured.out
