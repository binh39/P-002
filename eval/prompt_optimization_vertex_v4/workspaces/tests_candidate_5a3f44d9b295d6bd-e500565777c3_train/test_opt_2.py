# file: src\sample_repo\isort\isort\main.py:975-1058
# asked: {"lines": [975, 976, 977, 978, 979, 982, 983, 985, 986, 987, 988, 989, 992, 993, 994, 995, 996, 997, 1000, 1001, 1002, 1003, 1004, 1005, 1007, 1008, 1009, 1010, 1012, 1013, 1015, 1016, 1017, 1018, 1020, 1021, 1023, 1024, 1025, 1026, 1028, 1029, 1032, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1043, 1044, 1045, 1046, 1047, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1058], "branches": [[1035, 1036], [1035, 1043], [1050, 0], [1050, 1051], [1051, 1052], [1051, 1053], [1053, 1054], [1053, 1055], [1055, 1056], [1055, 1058]]}
# gained: {"lines": [975, 976, 977, 978, 979, 982, 983, 985, 986, 987, 988, 989, 992, 993, 994, 995, 996, 997, 1000, 1001, 1002, 1003, 1004, 1005, 1007, 1008, 1009, 1010, 1012, 1013, 1015, 1016, 1017, 1018, 1020, 1021, 1023, 1024, 1025, 1026, 1028, 1029, 1032, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1043, 1044, 1045, 1046, 1047, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1058], "branches": [[1035, 1036], [1035, 1043], [1050, 0], [1050, 1051], [1051, 1052], [1051, 1053], [1053, 1054], [1053, 1055], [1055, 1056], [1055, 1058]]}

import io
import sys
from unittest.mock import patch
from isort.main import identify_imports_main
from isort import api

def test_identify_imports_main_stdin(tmp_path):
    # Test file_names == ["-"] with stdin
    content = "import os\nfrom sys import version\n"
    stream = io.TextIOWrapper(io.BytesIO(content.encode("utf-8")))
    
    with patch("sys.stdout", new=io.StringIO()) as fake_out:
        identify_imports_main(argv=["-", "--unique", "--top-only", "--follow-links"], stdin=stream)
        output = fake_out.getvalue()
        assert "os" in output

def test_identify_imports_main_paths_variants(tmp_path):
    d = tmp_path / "sub"
    d.mkdir()
    p = d / "test_file.py"
    p.write_text("import os.path\nfrom collections import defaultdict\n")

    # Test default print (str(identified_import))
    with patch("sys.stdout", new=io.StringIO()) as fake_out:
        identify_imports_main(argv=[str(p)])
        assert "os.path" in fake_out.getvalue()

    # Test --packages (ImportKey.PACKAGE)
    with patch("sys.stdout", new=io.StringIO()) as fake_out:
        identify_imports_main(argv=[str(p), "--packages"])
        assert "os" in fake_out.getvalue()

    # Test --modules (ImportKey.MODULE)
    with patch("sys.stdout", new=io.StringIO()) as fake_out:
        identify_imports_main(argv=[str(p), "--modules"])
        assert "os.path" in fake_out.getvalue()

    # Test --attributes (ImportKey.ATTRIBUTE)
    with patch("sys.stdout", new=io.StringIO()) as fake_out:
        identify_imports_main(argv=[str(p), "--attributes"])
        # Should print module.attribute if present, or whatever find_imports returns
        # Let's write an import with attribute
        p.write_text("from os import path\n")
        identify_imports_main(argv=[str(p), "--attributes"])
        assert "os.path" in fake_out.getvalue()
