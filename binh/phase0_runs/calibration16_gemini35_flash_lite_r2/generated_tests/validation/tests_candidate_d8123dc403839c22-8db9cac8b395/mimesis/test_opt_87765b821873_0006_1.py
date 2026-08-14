# file: src\sample_repo\mimesis\mimesis\providers\internet.py:291-314
# asked: {"lines": [291, 293, 294, 295, 296, 297, 306, 307, 309, 311, 312, 314], "branches": [[311, 312], [311, 314]]}
# gained: {"lines": [291, 293, 294, 295, 296, 306, 307, 309, 311, 312, 314], "branches": [[311, 312], [311, 314]]}

import pytest
from mimesis.enums import PortRange, TLDType, URLScheme
from mimesis.providers.internet import Internet


@pytest.fixture
def internet():
    return Internet()


def test_url_default(internet):
    url = internet.url()
    assert url.startswith("https://")
    assert url.endswith("/")


def test_url_custom_parameters(internet):
    subdomains = ["test", "api"]
    url = internet.url(
        scheme=URLScheme.HTTP,
        port_range=PortRange.WELL_KNOWN,
        tld_type=TLDType.CCTLD,
        subdomains=subdomains,
    )
    assert url.startswith("http://")
    assert any(sub in url for sub in subdomains)
    assert ":" in url.split("://")[1]  # ensures port is present
    assert url.endswith("/")


def test_url_no_scheme_no_port(internet):
    url = internet.url(scheme=URLScheme.HTTPS, port_range=None)
    assert url.endswith("/")
