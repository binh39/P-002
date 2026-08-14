# file: src\sample_repo\mimesis\mimesis\providers\person.py:41-49
# asked: {"lines": [41, 42, 43, 45, 46, 48, 49], "branches": [[42, 43], [42, 45], [45, 46], [45, 48], [48, 0], [48, 49]]}
# gained: {"lines": [41, 42, 43, 45, 46, 48, 49], "branches": [[42, 43], [42, 45], [45, 46], [45, 48], [48, 49]]}

from datetime import datetime
import pytest
from mimesis.providers.person import Person


def test_validate_birth_year_params_min_greater_than_max():
    person = Person()
    with pytest.raises(ValueError, match="min_year must be less than or equal to max_year"):
        person._validate_birth_year_params(2000, 1999)


def test_validate_birth_year_params_min_less_than_1900():
    person = Person()
    with pytest.raises(ValueError, match="min_year must be greater than or equal to 1900"):
        person._validate_birth_year_params(1899, 2000)


def test_validate_birth_year_params_max_greater_than_current_year():
    person = Person()
    current_year = datetime.now().year
    with pytest.raises(ValueError, match="max_year must be less than or equal to the current year"):
        person._validate_birth_year_params(1990, current_year + 1)
