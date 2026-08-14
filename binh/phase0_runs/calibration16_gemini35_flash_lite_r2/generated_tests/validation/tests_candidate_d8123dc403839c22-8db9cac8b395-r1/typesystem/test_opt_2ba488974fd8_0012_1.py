# file: src\sample_repo\typesystem\typesystem\fields.py:607-664
# asked: {"lines": [607, 608, 609, 610, 611, 612, 613, 616, 617, 618, 620, 621, 622, 623, 624, 625, 626, 629, 630, 631, 632, 634, 635, 636, 637, 638, 639, 640, 641, 642, 644, 645, 647, 648, 649, 651, 653, 654, 655, 656, 657, 659, 661, 662, 664], "branches": [[608, 609], [608, 610], [610, 611], [610, 612], [612, 613], [612, 615], [615, 620], [615, 621], [621, 622], [621, 625], [622, 623], [622, 624], [625, 626], [625, 629], [631, 632], [631, 634], [634, 635], [634, 661], [636, 637], [636, 641], [637, 638], [637, 639], [639, 640], [639, 644], [641, 642], [641, 644], [644, 645], [644, 647], [648, 649], [648, 651], [653, 634], [653, 654], [654, 655], [654, 659], [661, 662], [661, 664]]}
# gained: {"lines": [607, 608, 609, 610, 611, 612, 613, 616, 617, 618, 620, 621, 622, 623, 624, 625, 626, 629, 630, 631, 632, 634, 635, 636, 637, 638, 639, 640, 641, 642, 644, 645, 647, 648, 649, 651, 653, 654, 655, 656, 657, 659, 661, 662, 664], "branches": [[608, 609], [608, 610], [610, 611], [610, 612], [612, 613], [612, 615], [615, 620], [615, 621], [621, 622], [621, 625], [622, 623], [622, 624], [625, 626], [625, 629], [631, 632], [631, 634], [634, 635], [634, 661], [636, 637], [636, 641], [637, 638], [637, 639], [639, 640], [641, 642], [641, 644], [644, 645], [644, 647], [648, 649], [648, 651], [653, 634], [653, 654], [654, 655], [654, 659], [661, 662], [661, 664]]}

import pytest
from typesystem.fields import Array, Field, String, Integer
from typesystem.base import ValidationError


def test_array_validate_none_allow_null():
    field = Array(allow_null=True)
    assert field.validate(None) is None


def test_array_validate_none_not_allowed():
    field = Array(allow_null=False)
    with pytest.raises(ValidationError) as exc:
        field.validate(None)
    assert exc.value.messages()[0].code == "null"


def test_array_validate_not_a_list():
    field = Array()
    with pytest.raises(ValidationError) as exc:
        field.validate("not-a-list")
    assert exc.value.messages()[0].code == "type"


def test_array_validate_exact_items():
    field = Array(exact_items=2)
    with pytest.raises(ValidationError) as exc:
        field.validate([1])
    assert exc.value.messages()[0].code == "exact_items"

    with pytest.raises(ValidationError) as exc:
        field.validate([1, 2, 3])
    assert exc.value.messages()[0].code == "exact_items"

    assert field.validate([1, 2]) == [1, 2]


def test_array_validate_min_items_empty():
    field = Array(min_items=1)
    with pytest.raises(ValidationError) as exc:
        field.validate([])
    assert exc.value.messages()[0].code == "empty"


def test_array_validate_min_items_general():
    field = Array(min_items=3)
    with pytest.raises(ValidationError) as exc:
        field.validate([1, 2])
    assert exc.value.messages()[0].code == "min_items"


def test_array_validate_max_items():
    field = Array(max_items=2)
    with pytest.raises(ValidationError) as exc:
        field.validate([1, 2, 3])
    assert exc.value.messages()[0].code == "max_items"


def test_array_validate_items_list_with_validator_and_additional():
    # items as list, testing position < len(items) vs additional_items
    field = Array(items=[Integer()], additional_items=String())
    
    # Valid validation
    validated = field.validate([1, "hello"])
    assert validated == [1, "hello"]

    # Invalid items in list validator
    with pytest.raises(ValidationError) as exc:
        field.validate(["not-an-int", "hello"])
    assert "type" in [m.code for m in exc.value.messages()]

    # Invalid additional items validator
    with pytest.raises(ValidationError) as exc:
        field.validate([1, 123])
    assert "type" in [m.code for m in exc.value.messages()]


def test_array_validate_single_item_validator_no_additional():
    field = Array(items=Integer())
    assert field.validate([1, 2, 3]) == [1, 2, 3]

    with pytest.raises(ValidationError) as exc:
        field.validate([1, "two", 3])
    assert len(exc.value.messages()) == 1
    assert exc.value.messages()[0].index == [1]


def test_array_validate_no_item_validator():
    field = Array(items=None)
    assert field.validate([1, "two", None]) == [1, "two", None]


def test_array_validate_unique_items():
    field = Array(unique_items=True)
    assert field.validate([1, 2, 3]) == [1, 2, 3]

    with pytest.raises(ValidationError) as exc:
        field.validate([1, 2, 1])
    assert exc.value.messages()[0].code == "unique_items"
    assert exc.value.messages()[0].index == [2]
