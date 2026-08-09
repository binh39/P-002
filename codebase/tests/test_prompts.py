import pytest

from src.modules.experiments.prompts import PromptBundle, baseline_prompt


def test_baseline_prompt_is_valid_and_stable():
    prompt = baseline_prompt()
    prompt.validate()
    assert prompt.digest() == baseline_prompt().digest()
    assert "Use get_info with a function, class, or Class.method name" in prompt.initial
    assert "Class.method" in prompt.initial
    assert "Prefer it to guessing APIs" in prompt.initial
    assert "get_info with a symbol name" in prompt.error
    assert "traceback" in prompt.error
    assert len(prompt.initial) < 500
    assert len(prompt.error) < 250


def test_prompt_rejects_missing_required_placeholder():
    with pytest.raises(ValueError, match="missing required placeholders"):
        PromptBundle(initial="{filename}", error="{error}").validate()
