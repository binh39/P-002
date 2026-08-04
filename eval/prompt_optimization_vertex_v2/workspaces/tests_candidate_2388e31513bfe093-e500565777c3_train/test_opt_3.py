# file: src\sample_repo\isort\isort\main.py:975-1058
# asked: {"lines": [975, 976, 977, 978, 979, 982, 983, 985, 986, 987, 988, 989, 992, 993, 994, 995, 996, 997, 1000, 1001, 1002, 1003, 1004, 1005, 1007, 1008, 1009, 1010, 1012, 1013, 1015, 1016, 1017, 1018, 1020, 1021, 1023, 1024, 1025, 1026, 1028, 1029, 1032, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1043, 1044, 1045, 1046, 1047, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1058], "branches": [[1035, 1036], [1035, 1043], [1050, 0], [1050, 1051], [1051, 1052], [1051, 1053], [1053, 1054], [1053, 1055], [1055, 1056], [1055, 1058]]}
# gained: {"lines": [975, 976, 977, 978, 979, 982, 983, 985, 986, 987, 988, 989, 992, 993, 994, 995, 996, 997, 1000, 1001, 1002, 1003, 1004, 1005, 1007, 1008, 1009, 1010, 1012, 1013, 1015, 1016, 1017, 1018, 1020, 1021, 1023, 1024, 1025, 1026, 1028, 1029, 1032, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1043, 1044, 1045, 1046, 1047, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1058], "branches": [[1035, 1036], [1035, 1043], [1050, 0], [1050, 1051], [1051, 1052], [1051, 1053], [1053, 1054], [1053, 1055], [1055, 1056], [1055, 1058]]}

import io
import sys
from unittest.mock import patch
from isort.main import identify_imports_main
from isort import api

def test_identify_imports_main_stdin(monkeypatch):
    stream = io.StringIO("import os\nfrom sys import path\n")
    with patch("isort.api.find_imports_in_stream") as mock_find:
        mock_find.return_value = []
        identify_imports_main(argv=["-"], stdin=stream)
        mock_find.assert_called_once_with(
            stream,
            unique=False,
            top_only=False,
            follow_links=False,
        )

def test_identify_imports_main_stdin_default_sys_stdin(monkeypatch):
    stream = io.StringIO("import os\n")
    monkeypatch.setattr(sys, "stdin", stream)
    with patch("isort.api.find_imports_in_stream") as mock_find:
        mock_find.return_value = []
        identify_imports_main(argv=["-"])
        mock_find.assert_called_once_with(
            stream,
            unique=False,
            top_only=False,
            follow_links=False,
        )

def test_identify_imports_main_paths_and_output_types(capsys):
    # Avoid creating files inside tmp_path if Windows holds handles or locks on it,
    # or just use a dummy string path since api functions are mocked anyway.
    dummy_path = "dummy_file.py"

    class DummyImport:
        def __init__(self, module, attribute):
            self.module = module
            self.attribute = attribute
        def __str__(self):
            return f"IMPORT {self.module}.{self.attribute}"

    dummy_imports = [
        DummyImport("os.path", "join"),
    ]

    with patch("isort.api.find_imports_in_paths", return_value=dummy_imports) as mock_find:
        # 1. Default (str(identified_import))
        identify_imports_main(argv=[dummy_path])
        captured = capsys.readouterr()
        assert "IMPORT os.path.join" in captured.out

        # 2. --packages (ImportKey.PACKAGE)
        mock_find.return_value = [DummyImport("os.path", "join")]
        identify_imports_main(argv=["--packages", dummy_path])
        captured = capsys.readouterr()
        assert "os\n" in captured.out

        # 3. --modules (ImportKey.MODULE)
        mock_find.return_value = [DummyImport("os.path", "join")]
        identify_imports_main(argv=["--modules", dummy_path])
        captured = capsys.readouterr()
        assert "os.path\n" in captured.out

        # 4. --attributes (ImportKey.ATTRIBUTE)
        mock_find.return_value = [DummyImport("os.path", "join")]
        identify_imports_main(argv=["--attributes", dummy_path])
        captured = capsys.readouterr()
        assert "os.path.join\n" in captured.out

        # 5. Test flags: --top-only, --follow-links, --unique
        identify_imports_main(argv=["--top-only", "--follow-links", "--unique", dummy_path])
        mock_find.assert_called_with(
            [dummy_path],
            unique=True,
            top_only=True,
            follow_links=True,
        )
