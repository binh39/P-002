"""Tests for the clone()/estimator-rebuild pitfall context in target_context.

These cover the E48 SFS diagnosis: the model's naive "add _estimator_type to the
instance" fix fails identically on every retry because SequentialFeatureSelector
rebuilds the wrapped estimator with clone() when clone_estimator=True. The failure
context should steer away from monkey-patching the instance.
"""

from pathlib import Path

import pytest


@pytest.fixture
def coverup_module():
    import importlib
    import sys

    if "src" not in sys.path:
        sys.path.insert(0, str(Path("src").resolve()))
    code_segment = importlib.import_module("coverup.segment").CodeSegment
    target_context = importlib.import_module("coverup.target_context")
    return code_segment, target_context._clone_pitfall_context


SOURCE_WITH_CLONE = (
    "class SFS:\n"
    "    def __init__(self, estimator, scoring=None, clone_estimator=True):\n"
    "        self.scoring = scoring\n"
    "        if self.clone_estimator:\n"
    "            self.est_ = clone(self.estimator)\n"
    "        if self.scoring is None:\n"
    "            if not hasattr(self.est_, '_estimator_type'):\n"
    "                raise AttributeError(\n"
    "                    \"Estimator must have an ._estimator_type\"\n"
    "                    \" for infering `scoring`\"\n"
    "                )\n"
    "    def fit(self, X, y):\n"
    "        pass\n"
)

ERROR_ESTIMATOR_TYPE = (
    "AttributeError: Estimator must have an ._estimator_type for infering `scoring`"
)


def _segment_for(tmp_path: Path, source: str, code_segment) -> object:
    p = tmp_path / "sfs_module.py"
    p.write_text(source, encoding="utf-8")
    # CodeSegment takes positional args: (filename, name, begin, end, qualname,
    # lines_of_interest, missing_lines, executed_lines, missing_branches, context, imports).
    return code_segment(
        p,
        "fit",
        0,
        len(source),
        "SFS.fit",
        {0},
        {0},
        set(),
        set(),
        [],
        [],
    )


def test_injects_when_estimator_type_and_clone_present(tmp_path, coverup_module):
    code_segment, pitfall = coverup_module
    seg = _segment_for(tmp_path, SOURCE_WITH_CLONE, code_segment)
    out = pitfall(seg, ERROR_ESTIMATOR_TYPE)
    assert out
    assert "_estimator_type" in out
    assert "clone_estimator=False" in out
    assert "monkey-patch" in out
    assert "scoring" in out


def test_no_injection_without_estimator_type_in_error(tmp_path, coverup_module):
    code_segment, pitfall = coverup_module
    seg = _segment_for(tmp_path, SOURCE_WITH_CLONE, code_segment)
    out = pitfall(seg, "ValueError: n_splits=5 too big")
    assert not out


def test_no_injection_without_clone_signal_in_source(tmp_path, coverup_module):
    code_segment, pitfall = coverup_module
    # Same estimator-protocol error, but the enclosing source has none of the
    # clone()/estimator-rebuild signals, so the pitfall hint must stay silent.
    source = (
        "class SFS:\n"
        "    def __init__(self, estimator, scoring=None):\n"
        "        self.estimator = estimator\n"
        "        self.scoring = scoring\n"
        "        if self.scoring is None:\n"
        "            if not hasattr(self.estimator, 'fit'):\n"
        "                raise AttributeError('estimator must have a fit method')\n"
        "    def fit(self, X, y):\n"
        "        return self.estimator.fit(X, y)\n"
    )
    seg = _segment_for(tmp_path, source, code_segment)
    out = pitfall(seg, ERROR_ESTIMATOR_TYPE)
    assert not out
