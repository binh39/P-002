# file: src\sample_repo\isort\isort\main.py:975-1058
# asked: {"lines": [975, 976, 977, 978, 979, 982, 983, 985, 986, 987, 988, 989, 992, 993, 994, 995, 996, 997, 1000, 1001, 1002, 1003, 1004, 1005, 1007, 1008, 1009, 1010, 1012, 1013, 1015, 1016, 1017, 1018, 1020, 1021, 1023, 1024, 1025, 1026, 1028, 1029, 1032, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1043, 1044, 1045, 1046, 1047, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1058], "branches": [[1035, 1036], [1035, 1043], [1050, 0], [1050, 1051], [1051, 1052], [1051, 1053], [1053, 1054], [1053, 1055], [1055, 1056], [1055, 1058]]}
# gained: {"lines": [975, 976, 977, 978, 979, 982, 983, 985, 986, 987, 988, 989, 992, 993, 994, 995, 996, 997, 1000, 1001, 1002, 1003, 1004, 1005, 1007, 1008, 1009, 1010, 1012, 1013, 1015, 1016, 1017, 1018, 1020, 1021, 1023, 1024, 1025, 1026, 1028, 1029, 1032, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1043, 1044, 1045, 1046, 1047, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1058], "branches": [[1035, 1036], [1035, 1043], [1050, 0], [1050, 1051], [1051, 1052], [1051, 1053], [1053, 1054], [1053, 1055], [1055, 1056], [1055, 1058]]}

import io
import sys
import tempfile
import os
import pytest
from isort import api
from isort.main import identify_imports_main


def test_identify_imports_main_stdin(capsys):
    # Test `file_names == ["-"]` branch and `stdin` provided explicitly,
    # plus default/else printing (`str(identified_import)`).
    code = "import os\n"
    stdin_stream = io.TextIOWrapper(io.BytesIO(code.encode("utf-8")), encoding="utf-8")

    identify_imports_main(argv=["-"], stdin=stdin_stream)
    captured = capsys.readouterr()
    assert "os" in captured.out


def test_identify_imports_main_paths_and_options(capsys):
    # Test `file_names != ["-"]` branch, `--top-only`, `--follow-links`,
    # and all uniqueness / print branches using standard tempfile to avoid Windows permission errors with pytest tmp_path.
    fd, path = tempfile.mkstemp(suffix=".py")
    os.close(fd)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("import os.path\nimport sys\n")

        # PACKAGE (--packages)
        identify_imports_main(argv=["--packages", path])
        captured = capsys.readouterr()
        assert "os" in captured.out

        # MODULE (--modules)
        identify_imports_main(argv=["--modules", path])
        captured = capsys.readouterr()
        assert "os.path" in captured.out or "sys" in captured.out

        # ATTRIBUTE (--attributes)
        fd2, path_attr = tempfile.mkstemp(suffix=".py")
        os.close(fd2)
        try:
            with open(path_attr, "w", encoding="utf-8") as f:
                f.write("from os import path\n")
            identify_imports_main(argv=["--attributes", path_attr])
            captured = capsys.readouterr()
            assert "os.path" in captured.out
        finally:
            if os.path.exists(path_attr):
                os.remove(path_attr)

        # --unique (True, hits the `else` branch of `arguments.unique == ...`)
        # and also exercise `--top-only` and `--follow-links`
        identify_imports_main(argv=["--unique", "--top-only", "--follow-links", path])
        captured = capsys.readouterr()
        assert "os.path" in captured.out
    finally:
        if os.path.exists(path):
            os.remove(path)
