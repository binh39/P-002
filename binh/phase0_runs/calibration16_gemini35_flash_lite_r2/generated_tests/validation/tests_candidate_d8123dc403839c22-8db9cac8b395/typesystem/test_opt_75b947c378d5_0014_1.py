# file: src\sample_repo\typesystem\typesystem\json_schema.py:150-171
# asked: {"lines": [150, 154, 156, 157, 158, 159, 161, 163, 165, 166, 168, 169, 170], "branches": [[156, 157], [156, 165], [165, 166], [165, 168]]}
# gained: {"lines": [150, 154, 156, 157, 158, 159, 161, 163, 165, 166, 168, 169, 170], "branches": [[156, 157], [156, 165], [165, 166], [165, 168]]}

from typesystem.json_schema import from_json_schema, type_from_json_schema, get_valid_types
from typesystem.schemas import Definitions
from typesystem.fields import Union, Const, Field
from typesystem.composites import NeverMatch

def test_type_from_json_schema_multiple_types():
    definitions = Definitions()
    schema = {"type": ["string", "integer"]}
    field = type_from_json_schema(schema, definitions=definitions)
    assert isinstance(field, Union)

def test_type_from_json_schema_no_types_allow_null():
    definitions = Definitions()
    schema = {"type": ["null"]}
    field = type_from_json_schema(schema, definitions=definitions)
    assert isinstance(field, Const)
    assert field.const is None

def test_type_from_json_schema_no_types_disallow_null():
    definitions = Definitions()
    # When `type` is empty list, get_valid_types populates all types (string, boolean, object, array, number, string),
    # minus null (allow_null = False). Thus len(type_strings) > 1, returning a Union.
    # To directly test len(type_strings) == 0 with allow_null = False, we can call type_from_json_schema
    # by directly passing a dict where get_valid_types returns an empty set and allow_null=False,
    # or by testing the lines via code simulation / monkeypatching if needed, or by testing get_valid_types directly.
    # But wait, let's see how we can hit line 165 (len(type_strings) == 0) with allow_null=False.
    # If data has no 'type' field at all, get_valid_types() returns 6 types (not empty).
    # If data has 'type': [], get_valid_types() returns empty type_strings and allow_null=False.
    # Wait, let's check get_valid_types:
    # type_strings = data.get('type', []) -> []
    # if not type_strings: type_strings = {'null', 'boolean', 'object', 'array', 'number', 'string'}
    # So `type` being [] actually resets to all types!
    # To get an empty type_strings with allow_null=False, how is it possible?
    # If 'type': 'invalid' or something? No, get_valid_types does:
    # type_strings = data.get('type', [])
    # if isinstance(type_strings, str): type_strings = {type_strings}
    # if not type_strings: type_strings = ...
    # if 'null' in type_strings: allow_null = True; type_strings.remove('null')
    # So type_strings is ONLY empty if 'type' is ['null']. In that case allow_null = True.
    # What if we patch get_valid_types or call type_from_json_schema when type_strings is empty?
    # Let's use monkeypatch to test len(type_strings) == 0 and allow_null = False:
    import typesystem.json_schema
    orig_get_valid_types = typesystem.json_schema.get_valid_types
    try:
        typesystem.json_schema.get_valid_types = lambda data: (set(), False)
        field = type_from_json_schema({}, definitions=definitions)
        assert isinstance(field, NeverMatch)
    finally:
        typesystem.json_schema.get_valid_types = orig_get_valid_types

def test_type_from_json_schema_single_type():
    definitions = Definitions()
    schema = {"type": "string"}
    field = type_from_json_schema(schema, definitions=definitions)
    assert field.allow_null is False
