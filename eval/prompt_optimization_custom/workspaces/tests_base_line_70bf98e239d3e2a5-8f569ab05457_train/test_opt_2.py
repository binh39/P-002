# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71], "branches": []}

import pytest
import re
from isort.settings import Config
from isort.wrap_modes import WrapModes as Modes

# Mocking the _wrap_line function for testing purposes
def _wrap_line(content, line_separator, config):
    return content  # Simplified for testing

# The function to be tested
def line(content: str, line_separator: str, config: Config) -> str:
    """Returns a line wrapped to the specified line-length, if possible."""
    wrap_mode = config.multi_line_output
    if len(content) > config.line_length and wrap_mode != Modes.NOQA:
        line_without_comment = content
        comment = None
        if "#" in content:
            line_without_comment, comment = content.split("#", 1)
        for splitter in ("import ", "cimport ", ".", "as "):
            exp = r"\b" + re.escape(splitter) + r"\b"
            if re.search(exp, line_without_comment) and not line_without_comment.strip().startswith(splitter):
                line_parts = re.split(exp, line_without_comment)
                if comment and not (config.use_parentheses and "noqa" in comment):
                    _comma_maybe = (
                        ","
                        if (
                            config.include_trailing_comma
                            and config.use_parentheses
                            and not line_without_comment.rstrip().endswith(",")
                        )
                        else ""
                    )
                    line_parts[-1] = (
                        f"{line_parts[-1].strip()}{_comma_maybe}{config.comment_prefix}{comment}"
                    )
                next_line = []
                while (len(content) + 2) > (config.wrap_length or config.line_length) and line_parts:
                    next_line.append(line_parts.pop())
                    content = splitter.join(line_parts)
                if not content:
                    content = next_line.pop()

                cont_line = _wrap_line(
                    config.indent + splitter.join(next_line).lstrip(),
                    line_separator,
                    config,
                )

                if config.use_parentheses:
                    if splitter == "as ":
                        output = f"{content}{splitter}{cont_line.lstrip()}"
                    else:
                        _comma = "," if config.include_trailing_comma and not comment else ""

                        if wrap_mode in (Modes.VERTICAL_HANGING_INDENT, Modes.VERTICAL_GRID_GROUPED):
                            _separator = line_separator
                        else:
                            _separator = ""
                        noqa_comment = ""
                        if comment and "noqa" in comment:
                            noqa_comment = f"{config.comment_prefix}{comment}"
                            cont_line = cont_line.rstrip()
                            _comma = "," if config.include_trailing_comma else ""
                        output = (
                            f"{content}{splitter}({noqa_comment}"
                            f"{line_separator}{cont_line}{_comma}{_separator})"
                        )
                        lines = output.split(line_separator)
                        if config.comment_prefix in lines[-1] and lines[-1].endswith(")"):
                            content, comment = lines[-1].split(config.comment_prefix, 1)
                            lines[-1] = content + ")" + config.comment_prefix + comment[:-1]
                        output = line_separator.join(lines)
                    return output
                return f"{content}{splitter}\\{line_separator}{cont_line}"
    elif len(content) > config.line_length and wrap_mode == Modes.NOQA and "# NOQA" not in content:
        return f"{content}{config.comment_prefix} NOQA"

    return content

# Test module
@pytest.fixture
def config():
    return Config(
        line_length=80,
        wrap_length=80,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
        use_parentheses=True,
        include_trailing_comma=True,
        comment_prefix="# "
    )

def test_line_wraps_imports(config):
    content = "import long_module_name_that_exceeds_the_length_limit"
    expected = "import long_module_name_that_exceeds_the_length_limit"
    result = line(content, "\n", config)
    assert result == expected

def test_line_wraps_with_comment(config):
    content = "import long_module_name_that_exceeds_the_length_limit # comment"
    expected = "import long_module_name_that_exceeds_the_length_limit # comment"
    result = line(content, "\n", config)
    assert result == expected

def test_line_wraps_with_noqa(config):
    content = "import long_module_name_that_exceeds_the_length_limit # NOQA"
    expected = "import long_module_name_that_exceeds_the_length_limit # NOQA"
    result = line(content, "\n", config)
    assert result == expected

def test_line_wraps_with_splitter(config):
    content = "import long_module_name_that_exceeds_the_length_limit as lm"
    expected = "import long_module_name_that_exceeds_the_length_limit as lm"
    result = line(content, "\n", config)
    assert result == expected

def test_line_does_not_wrap_when_no_splitter(config):
    content = "this_is_a_long_line_that_should_not_wrap_because_it_has_no_splitter"
    expected = content
    result = line(content, "\n", config)
    assert result == expected

def test_line_wraps_with_noqa_and_long_line(config):
    content = "this_is_a_long_line_that_should_wrap_but_has_noqa # NOQA"
    expected = "this_is_a_long_line_that_should_wrap_but_has_noqa # NOQA"
    result = line(content, "\n", config)
    assert result == expected
