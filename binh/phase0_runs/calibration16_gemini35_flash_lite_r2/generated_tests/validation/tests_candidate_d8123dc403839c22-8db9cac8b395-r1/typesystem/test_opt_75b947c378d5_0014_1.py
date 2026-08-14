# file: src\sample_repo\typesystem\typesystem\json_schema.py:150-171
# asked: {"lines": [150, 154, 156, 157, 158, 159, 161, 163, 165, 166, 168, 169, 170], "branches": [[156, 157], [156, 165], [165, 166], [165, 168]]}
# gained: {"lines": [150, 154, 156, 157, 158, 159, 161, 163, 165, 166, 168, 169, 170], "branches": [[156, 157], [156, 165], [165, 166], [165, 168]]}

from typesystem.json_schema import from_json_schema, type_from_json_schema
from typesystem.schemas import Definitions
from typesystem.fields import Union, Const, String, Integer
from typesystem.composites import NeverMatch

def test_type_from_json_schema_branches():
    definitions = Definitions()

    # 1. len(type_strings) > 1 -> Union
    schema_union = {"type": ["string", "integer"]}
    field_union = type_from_json_schema(schema_union, definitions)
    assert isinstance(field_union, Union)
    assert field_union.allow_null is False

    # Union with null (multiple types + null)
    schema_union_null = {"type": ["string", "integer", "null"]}
    field_union_null = type_from_json_schema(schema_union_null, definitions)
    assert isinstance(field_union_null, Union)
    assert field_union_null.allow_null is True

    # 2. len(type_strings) == 0: allow_null = True -> Const(None)
    schema_empty_null = {"type": "null"}
    field_null = type_from_json_schema(schema_empty_null, definitions)
    assert isinstance(field_null, Const)
    assert field_null.const is None

    # 3. len(type_strings) == 0: allow_null = False -> NeverMatch()
    import typesystem.json_schema as js_module
    original_get_valid_types = js_module.get_valid_types
    try:
        js_module.get_valid_types = lambda data: (set(), False)
        field_never = type_from_json_schema({}, definitions)
        assert isinstance(field_never, NeverMatch)
    finally:
        js_module.get_valid_types = original_get_valid_types

    # 4. len(type_strings) == 1 -> single type execution (lines 168-170)
    schema_single = {"type": "string", "minLength": 3}
    field_single = type_from_json_schema(schema_single, definitions)
    assert isinstance(field_single, String)
    assert field_single.min_length == 3
