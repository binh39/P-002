import pytest

from backend.modules.experiments.prompts import PromptBundle, baseline_prompt


def test_baseline_prompt_is_valid_and_stable():
    prompt = baseline_prompt()
    prompt.validate()
    assert prompt.digest() == baseline_prompt().digest()
    assert "Use get_info(name)" in prompt.initial
    assert "source/signatures" in prompt.initial
    assert "Do not guess APIs" in prompt.initial
    assert "Use get_info(name)" in prompt.error
    assert "traceback" in prompt.error
    assert len(prompt.initial) < 400
    assert len(prompt.error) < 180


def test_prompt_rejects_missing_required_placeholder():
    with pytest.raises(ValueError, match="missing required placeholders"):
        PromptBundle(initial="{filename}", error="{error}").validate()
