# file: src\sample_repo\typesystem\typesystem\fields.py:607-664
# asked: {"lines": [607, 608, 609, 610, 611, 612, 613, 616, 617, 618, 620, 621, 622, 623, 624, 625, 626, 629, 630, 631, 632, 634, 635, 636, 637, 638, 639, 640, 641, 642, 644, 645, 647, 648, 649, 651, 653, 654, 655, 656, 657, 659, 661, 662, 664], "branches": [[608, 609], [608, 610], [610, 611], [610, 612], [612, 613], [612, 615], [615, 620], [615, 621], [621, 622], [621, 625], [622, 623], [622, 624], [625, 626], [625, 629], [631, 632], [631, 634], [634, 635], [634, 661], [636, 637], [636, 641], [637, 638], [637, 639], [639, 640], [639, 644], [641, 642], [641, 644], [644, 645], [644, 647], [648, 649], [648, 651], [653, 634], [653, 654], [654, 655], [654, 659], [661, 662], [661, 664]]}
# gained: {"lines": [607, 608, 609, 610, 611, 612, 613, 616, 617, 618, 620, 621, 622, 623, 624, 625, 626, 629, 630, 631, 632, 634, 635, 636, 637, 638, 639, 640, 641, 642, 644, 645, 647, 648, 649, 651, 653, 654, 655, 656, 657, 659, 661, 662, 664], "branches": [[608, 609], [608, 610], [610, 611], [610, 612], [612, 613], [612, 615], [615, 620], [615, 621], [621, 622], [621, 625], [622, 623], [622, 624], [625, 626], [625, 629], [631, 632], [631, 634], [634, 635], [634, 661], [636, 637], [636, 641], [637, 638], [637, 639], [639, 640], [641, 642], [641, 644], [644, 645], [644, 647], [648, 649], [648, 651], [653, 634], [653, 654], [654, 655], [654, 659], [661, 662], [661, 664]]}

import pytest
from typesystem.fields import Array, Field, Integer, String
from typesystem.base import ValidationError


def test_array_validate_none_allow_null():
    field = Array(allow_null=True)
    assert field.validate(None) is None


def test_array_validate_none_disallowed():
    field = Array(allow_null=False)
    with pytest.raises(ValidationError) as exc_info:
        field.validate(None)
    assert exc_info.value.messages()[0].code == "null"


def test_array_validate_invalid_type():
    field = Array()
    with pytest.raises(ValidationError) as exc_info:
        field.validate("not-a-list")
    assert exc_info.value.messages()[0].code == "type"


def test_array_validate_exact_items():
    field = Array(exact_items=2, items=Integer())
    
    # Valid exact items
    assert field.validate([1, 2]) == [1, 2]
    
    # Invalid exact items length
    with pytest.raises(ValidationError) as exc_info:
        field.validate([1])
    assert exc_info.value.messages()[0].code == "exact_items"


def test_array_validate_min_items_empty():
    field = Array(min_items=1)
    with pytest.raises(ValidationError) as exc_info:
        field.validate([])
    assert exc_info.value.messages()[0].code == "empty"


def test_array_validate_min_items_general():
    field = Array(min_items=3)
    with pytest.raises(ValidationError) as exc_info:
        field.validate([1, 2])
    assert exc_info.value.messages()[0].code == "min_items"


def test_array_validate_max_items():
    field = Array(max_items=2)
    with pytest.raises(ValidationError) as exc_info:
        field.validate([1, 2, 3])
    assert exc_info.value.messages()[0].code == "max_items"


def test_array_validate_items_list_and_additional_items():
    # Test items as a list, with additional_items as a Field
    field = Array(items=[Integer()], additional_items=String())
    
    # Valid positional items and additional items
    res = field.validate([1, "hello"])
    assert res == [1, "hello"]

    # Invalid positional item
    with pytest.raises(ValidationError) as exc_info:
        field.validate(["not-an-int", "hello"])
    assert any(m.code == "type" for m in exc_info.value.messages())

    # Invalid additional item
    with pytest.raises(ValidationError) as exc_info:
        field.validate([1, 123])
    assert any(m.code == "type" for m in exc_info.value.messages())


def test_array_validate_single_validator():
    field = Array(items=Integer())
    assert field.validate([1, 2, 3]) == [1, 2, 3]

    with pytest.raises(ValidationError) as exc_info:
        field.validate([1, "two", 3])
    assert any(m.code == "type" for m in exc_info.value.messages())


def test_array_validate_no_validator():
    field = Array()
    assert field.validate([1, "two", None]) == [1, "two", None]


def test_array_validate_unique_items():
    field = Array(unique_items=True)
    
    # Unique items pass
    assert field.validate([1, 2, 3]) == [1, 2, 3]

    # Duplicate items raise error
    with pytest.raises(ValidationError) as exc_info:
        field.validate([1, 2, 1])
    
    messages = exc_info.value.messages()
    assert any(m.code == "unique_items" for m in messages)
