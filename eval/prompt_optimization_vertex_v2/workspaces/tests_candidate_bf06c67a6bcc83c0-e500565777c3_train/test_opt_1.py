# file: src\sample_repo\isort\isort\main.py:975-1058
# asked: {"lines": [975, 976, 977, 978, 979, 982, 983, 985, 986, 987, 988, 989, 992, 993, 994, 995, 996, 997, 1000, 1001, 1002, 1003, 1004, 1005, 1007, 1008, 1009, 1010, 1012, 1013, 1015, 1016, 1017, 1018, 1020, 1021, 1023, 1024, 1025, 1026, 1028, 1029, 1032, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1043, 1044, 1045, 1046, 1047, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1058], "branches": [[1035, 1036], [1035, 1043], [1050, 0], [1050, 1051], [1051, 1052], [1051, 1053], [1053, 1054], [1053, 1055], [1055, 1056], [1055, 1058]]}
# gained: {"lines": [975, 976, 977, 978, 979, 982, 983, 985, 986, 987, 988, 989, 992, 993, 994, 995, 996, 997, 1000, 1001, 1002, 1003, 1004, 1005, 1007, 1008, 1009, 1010, 1012, 1013, 1015, 1016, 1017, 1018, 1020, 1021, 1023, 1024, 1025, 1026, 1028, 1029, 1032, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1043, 1044, 1045, 1046, 1047, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1058], "branches": [[1035, 1036], [1035, 1043], [1050, 0], [1050, 1051], [1051, 1052], [1051, 1053], [1053, 1054], [1053, 1055], [1055, 1056], [1055, 1058]]}

import io
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest

from isort.main import identify_imports_main
from isort import api


def test_identify_imports_main_stdin(capsys):
    stream_content = "import os\nfrom sys import path\n"
    stream = io.StringIO(stream_content)
    
    identify_imports_main(argv=["-"], stdin=stream)
    captured = capsys.readouterr()
    assert "os" in captured.out or "path" in captured.out


def test_identify_imports_main_paths_and_unique_branches(capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "sample.py"
        file_path.write_text("import os.path as p\nimport math\n")

        # Test unique = False (default branch)
        identify_imports_main(argv=[str(file_path)])
        captured = capsys.readouterr()
        assert "os.path" in captured.out or "math" in captured.out

        # Test --packages (ImportKey.PACKAGE)
        identify_imports_main(argv=["--packages", str(file_path)])
        captured = capsys.readouterr()
        assert len(captured.out.strip()) > 0

        # Test --modules (ImportKey.MODULE)
        identify_imports_main(argv=["--modules", str(file_path)])
        captured = capsys.readouterr()
        assert len(captured.out.strip()) > 0

        # Test --attributes (ImportKey.ATTRIBUTE)
        identify_imports_main(argv=["--attributes", str(file_path)])
        captured = capsys.readouterr()

        # Test --unique (True, but not an enum)
        identify_imports_main(argv=["--unique", str(file_path)])
        captured = capsys.readouterr()
        assert len(captured.out.strip()) > 0

        # Test --top-only and --follow-links
        identify_imports_main(argv=["--top-only", "--follow-links", str(file_path)])
        captured = capsys.readouterr()
        assert len(captured.out.strip()) > 0
