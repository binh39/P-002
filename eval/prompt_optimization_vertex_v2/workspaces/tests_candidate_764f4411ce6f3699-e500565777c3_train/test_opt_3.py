# file: src\sample_repo\isort\isort\main.py:975-1058
# asked: {"lines": [975, 976, 977, 978, 979, 982, 983, 985, 986, 987, 988, 989, 992, 993, 994, 995, 996, 997, 1000, 1001, 1002, 1003, 1004, 1005, 1007, 1008, 1009, 1010, 1012, 1013, 1015, 1016, 1017, 1018, 1020, 1021, 1023, 1024, 1025, 1026, 1028, 1029, 1032, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1043, 1044, 1045, 1046, 1047, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1058], "branches": [[1035, 1036], [1035, 1043], [1050, 0], [1050, 1051], [1051, 1052], [1051, 1053], [1053, 1054], [1053, 1055], [1055, 1056], [1055, 1058]]}
# gained: {"lines": [975, 976, 977, 978, 979, 982, 983, 985, 986, 987, 988, 989, 992, 993, 994, 995, 996, 997, 1000, 1001, 1002, 1003, 1004, 1005, 1007, 1008, 1009, 1010, 1012, 1013, 1015, 1016, 1017, 1018, 1020, 1021, 1023, 1024, 1025, 1026, 1028, 1029, 1032, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1043, 1044, 1045, 1046, 1047, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1058], "branches": [[1035, 1036], [1035, 1043], [1050, 0], [1050, 1051], [1051, 1052], [1051, 1053], [1053, 1054], [1053, 1055], [1055, 1056], [1055, 1058]]}

import io
import sys
import tempfile
from pathlib import Path
import pytest

from isort.main import identify_imports_main
from isort import api


def test_identify_imports_main_stdin(capsys):
    """Test identify_imports_main reading from stdin using '-'."""
    stream_content = "import os\nfrom sys import path\n"
    stdin_wrapper = io.TextIOWrapper(io.BytesIO(stream_content.encode("utf-8")))

    identify_imports_main(argv=["-"], stdin=stdin_wrapper)
    captured = capsys.readouterr()
    assert "os" in captured.out or "path" in captured.out


def test_identify_imports_main_files_and_options(capsys):
    """Test identify_imports_main with real files using tempfile, --top-only, --follow-links, and various uniqueness options."""
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "test_file.py"
        p.write_text("import os\nfrom collections import defaultdict\n\ndef foo():\n    import sys\n", encoding="utf-8")

        # Test path branch (not '-')
        identify_imports_main(argv=[str(p), "--top-only", "--follow-links"])
        captured = capsys.readouterr()
        assert "os" in captured.out

        # Test PACKAGE unique
        identify_imports_main(argv=[str(p), "--packages"])
        captured = capsys.readouterr()
        assert len(captured.out) > 0

        # Test MODULE unique
        identify_imports_main(argv=[str(p), "--modules"])
        captured = capsys.readouterr()
        assert len(captured.out) > 0

        # Test ATTRIBUTE unique
        identify_imports_main(argv=[str(p), "--attributes"])
        captured = capsys.readouterr()

        # Test general unique
        identify_imports_main(argv=[str(p), "--unique"])
        captured = capsys.readouterr()
        assert len(captured.out) > 0
