# file: src\sample_repo\mimesis\mimesis\providers\person.py:200-256
# asked: {"lines": [200, 201, 202, 228, 229, 231, 232, 234, 235, 237, 238, 239, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 256], "branches": [[228, 229], [228, 231], [231, 232], [231, 234], [237, 238], [237, 242], [243, 244], [243, 256], [245, 246], [245, 247], [247, 248], [247, 249], [249, 250], [249, 251], [251, 252], [251, 253], [253, 243], [253, 254]]}
# gained: {"lines": [200, 201, 228, 229, 231, 232, 234, 235, 237, 238, 239, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 256], "branches": [[228, 229], [228, 231], [231, 232], [231, 234], [237, 238], [237, 242], [243, 244], [243, 256], [245, 246], [245, 247], [247, 248], [247, 249], [249, 250], [249, 251], [251, 252], [251, 253], [253, 243], [253, 254]]}

import pytest
from mimesis.providers.person import Person


def test_username_drange_invalid_length():
    person = Person()
    with pytest.raises(ValueError, match="The drange parameter must contain only two integers."):
        person.username(drange=(1800,))


def test_username_default_mask():
    person = Person()
    result = person.username()
    assert isinstance(result, str)
    assert "_" in result


def test_username_invalid_mask():
    person = Person()
    with pytest.raises(ValueError, match=r"Username mask must contain at least one of these"):
        person.username(mask="123")


def test_username_all_tags_and_separators():
    person = Person()
    # Mask containing C, U, l, d, and separators -, _, .
    mask = "C-U_l.d"
    result = person.username(mask=mask, drange=(2000, 2005))
    assert isinstance(result, str)
    assert "-" in result
    assert "_" in result
    assert "." in result
