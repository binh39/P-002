import importlib.util
import os
import socket

import pytest

from demo import classify


def test_optimizer_candidate_runs_only_in_project_sandbox():
    assert classify(2) == "positive"
    assert importlib.util.find_spec("gepa") is None
    assert importlib.util.find_spec("coverup") is None
    assert not any(name.startswith(("AWS_", "GOOGLE_", "AZURE_")) for name in os.environ)
    with pytest.raises(OSError):
        socket.create_connection(("1.1.1.1", 53), timeout=1)
