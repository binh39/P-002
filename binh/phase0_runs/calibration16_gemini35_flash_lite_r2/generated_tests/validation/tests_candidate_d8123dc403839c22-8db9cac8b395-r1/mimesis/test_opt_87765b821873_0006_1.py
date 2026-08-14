# file: src\sample_repo\mimesis\mimesis\providers\internet.py:291-314
# asked: {"lines": [291, 293, 294, 295, 296, 297, 306, 307, 309, 311, 312, 314], "branches": [[311, 312], [311, 314]]}
# gained: {"lines": [291, 293, 294, 295, 296, 306, 307, 309, 311, 312, 314], "branches": [[311, 312], [311, 314]]}

import pytest
from mimesis import Internet
from mimesis.enums import PortRange, TLDType, URLScheme


def test_url_default():
    internet = Internet()
    res = internet.url()
    assert res.startswith("https://")
    assert res.endswith("/")


def test_url_custom_parameters():
    internet = Internet()
    res = internet.url(
        scheme=URLScheme.HTTP,
        port_range=PortRange.WELL_KNOWN,
        tld_type=TLDType.CCTLD,
        subdomains=["test"],
    )
    assert res.startswith("http://")
    assert "test." in res
    assert ":" in res.split("://")[1]
    assert res.endswith("/")


def test_url_none_scheme_and_port():
    internet = Internet()
    res = internet.url(
        scheme=None,
        port_range=None,
    )
    assert isinstance(res, str)
    assert res.endswith("/")
