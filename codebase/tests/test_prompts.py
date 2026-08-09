import pytest

from src.modules.experiments.prompts import PromptBundle, baseline_prompt


def test_baseline_prompt_is_valid_and_stable():
    prompt = baseline_prompt()
    prompt.validate()
    assert prompt.digest() == baseline_prompt().digest()
    assert len(prompt.initial) < 300
    assert "deterministic" not in prompt.initial
    assert len(prompt.error) < 150


def test_prompt_rejects_missing_required_placeholder():
    with pytest.raises(ValueError, match="missing required placeholders"):
        PromptBundle(initial="{filename}", error="{error}").validate()
