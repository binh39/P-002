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
    return (
        code_segment,
        target_context._clone_pitfall_context,
        target_context._private_test_hook_context,
        target_context.build_failure_context,
        target_context._sfs_branch_completion_context,
    )


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
    code_segment, pitfall, _private, _build, _sfs = coverup_module
    seg = _segment_for(tmp_path, SOURCE_WITH_CLONE, code_segment)
    out = pitfall(seg, ERROR_ESTIMATOR_TYPE)
    assert out
    assert "_estimator_type" in out
    assert "clone_estimator=False" in out
    assert "monkey-patch" in out
    assert "scoring='accuracy'" in out
    # The stale "use an estimator that declares _estimator_type" advice is gone
    # because no sklearn estimator exposes it in this env.
    assert "declares `_estimator_type`" not in out


def test_no_injection_without_estimator_type_in_error(tmp_path, coverup_module):
    code_segment, pitfall, _private, _build, _sfs = coverup_module
    seg = _segment_for(tmp_path, SOURCE_WITH_CLONE, code_segment)
    out = pitfall(seg, "ValueError: n_splits=5 too big")
    assert not out


def test_no_injection_without_clone_signal_in_source(tmp_path, coverup_module):
    code_segment, pitfall, _private, _build, _sfs = coverup_module
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


def test_private_hook_injected_when_testing_hook_in_error(coverup_module):
    _code_segment, _pitfall, private, _build, _sfs = coverup_module
    error = (
        "Failed: DID NOT RAISE KeyboardInterrupt\n"
        ">       with pytest.raises(KeyboardInterrupt):\n"
        "E       Failed: DID NOT RAISE KeyboardInterrupt\n"
        "_TESTING_INTERRUPT_MODE"
    )
    out = private(error)
    assert out
    assert "private `_TESTING_*`" in out
    assert "DID NOT RAISE KeyboardInterrupt" in out


def test_private_hook_silent_without_testing_hook(coverup_module):
    _code_segment, _pitfall, private, _build, _sfs = coverup_module
    out = private("AttributeError: Estimator must have an ._estimator_type")
    assert not out


def test_build_failure_context_includes_private_hook_section(tmp_path, coverup_module):
    code_segment, _pitfall, _private, build, _sfs = coverup_module
    seg = _segment_for(tmp_path, SOURCE_WITH_CLONE, code_segment)
    error = (
        "Failed: DID NOT RAISE KeyboardInterrupt\n"
        "sfs._TESTING_INTERRUPT_MODE = True\n"
        "E       Failed: DID NOT RAISE KeyboardInterrupt"
    )
    out = build(seg, error)
    assert "[PRIVATE TEST HOOK]" in out
    assert "[CLONE/REBUILD PITFALL]" not in out


SOURCE_WITH_SFS_BRANCHES = (
    "class SequentialFeatureSelector:\n"
    "    def fit(self, X, y):\n"
    "        self.k_features = self.k_features\n"
    "        self.feature_groups = self.feature_groups\n"
    "        if len({type(i) for i in self.fixed_features_}) > 1:\n"
    "            raise ValueError('fixed_features values must have the same type')\n"
    "        if self.floating:\n"
    "            self._feature_selector(self.forward)\n"
    "    def _feature_selector(self, forward):\n"
    "        pass\n"
)


def test_sfs_branch_completion_injected(tmp_path, coverup_module):
    code_segment, _pitfall, _private, _build, sfs = coverup_module
    seg = _segment_for(tmp_path, SOURCE_WITH_SFS_BRANCHES, code_segment)
    out = sfs(seg, "ValueError: fixed_features values must have the same type")
    assert out
    assert "parsimonious" in out
    assert "floating" in out
    assert "k_features" in out


def test_sfs_branch_completion_silent_without_validation_error(tmp_path, coverup_module):
    code_segment, _pitfall, _private, _build, sfs = coverup_module
    seg = _segment_for(tmp_path, SOURCE_WITH_SFS_BRANCHES, code_segment)
    out = sfs(seg, "ImportError: cannot import name 'weird'")
    assert not out


def test_sfs_branch_completion_silent_without_sfs_markers(tmp_path, coverup_module):
    code_segment, _pitfall, _private, _build, sfs = coverup_module
    seg = _segment_for(tmp_path, SOURCE_WITH_CLONE, code_segment)
    out = sfs(seg, "ValueError: fixed_features values must have the same type")
    assert not out


def test_build_failure_context_includes_sfs_branch_section(tmp_path, coverup_module):
    code_segment, _pitfall, _private, build, _sfs = coverup_module
    seg = _segment_for(tmp_path, SOURCE_WITH_SFS_BRANCHES, code_segment)
    out = build(seg, "ValueError: fixed_features values must have the same type")
    assert "[SFS BRANCH COMPLETION]" in out
    assert "floating-backward loop" in out
