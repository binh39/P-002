# file: src\sample_repo\mimesis\mimesis\providers\internet.py:219-236
# asked: {"lines": [219, 233, 234, 235, 236], "branches": []}
# gained: {"lines": [219, 233, 234, 235, 236], "branches": []}

from mimesis.providers.internet import Internet
from mimesis.datasets import CLOUD_REGION_DIRECTIONS, CLOUD_REGION_PREFIXES


def test_cloud_region():
    internet = Internet()
    region = internet.cloud_region()
    assert isinstance(region, str)
    
    parts = region.split("-")
    assert len(parts) == 3
    assert parts[0] in CLOUD_REGION_PREFIXES
    assert parts[1] in CLOUD_REGION_DIRECTIONS
    assert parts[2].isdigit()
    assert 1 <= int(parts[2]) <= 5


def test_cloud_region_custom_separator():
    internet = Internet()
    region = internet.cloud_region(separator="_")
    assert isinstance(region, str)
    
    parts = region.split("_")
    assert len(parts) == 3
    assert parts[0] in CLOUD_REGION_PREFIXES
    assert parts[1] in CLOUD_REGION_DIRECTIONS
    assert parts[2].isdigit()
    assert 1 <= int(parts[2]) <= 5
