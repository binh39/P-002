# file: sample_repo\isort\isort\format.py:76-85
# asked: {"lines": [76, 77, 78, 79, 80, 81, 82, 83, 84, 85], "branches": [[78, 79], [78, 85], [81, 82], [81, 83], [83, 78], [83, 84]]}
# gained: {"lines": [76, 77, 78, 79, 80, 81, 82, 83, 84, 85], "branches": [[78, 79], [78, 85], [81, 82], [81, 83], [83, 78], [83, 84]]}

import pytest
from unittest.mock import patch
from isort.format import ask_whether_to_apply_changes_to_file

def test_apply_changes_yes():
    with patch('builtins.input', return_value='y'):
        result = ask_whether_to_apply_changes_to_file('test_file.py')
        assert result is True

def test_apply_changes_no():
    with patch('builtins.input', return_value='n'):
        result = ask_whether_to_apply_changes_to_file('test_file.py')
        assert result is False

def test_apply_changes_quit():
    with patch('builtins.input', return_value='q'):
        with pytest.raises(SystemExit):
            ask_whether_to_apply_changes_to_file('test_file.py')
