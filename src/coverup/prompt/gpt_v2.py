import json
from collections.abc import Callable

import coverup.codeinfo as codeinfo

from ..segment import CodeSegment
from .prompter import Prompter, mk_message


class GptV2Prompter(Prompter):
    """Prompter for GPT 4."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.templates = {}
        if template_file := getattr(self.args, "prompt_template_file", None):
            with template_file.open(encoding="utf-8") as f:
                self.templates = json.load(f)

    def _render(self, name: str, default: str, **values) -> str:
        template = self.templates.get(name, default)
        return template.format(**values)


    def initial_prompt(self, segment: CodeSegment) -> list[dict]:
        filename = segment.path.relative_to(self.args.src_base_dir)
        if "initial" in self.templates:
            return [mk_message(self._render(
                "initial", self.templates["initial"],
                filename=filename,
                coverage_targets=segment.lines_branches_missing_do(),
                source_excerpt=segment.get_excerpt(),
            ))]

        return [
            mk_message(f"""
You are an expert Python test-driven developer.
The code below, extracted from {filename}, does not achieve full coverage:
when tested, {segment.lines_branches_missing_do()} not execute.
Create new pytest test functions that execute all missing lines and branches, always making
sure that each test is correct and indeed improves coverage.
Use the get_info tool function as necessary.
Always send entire Python test scripts when proposing a new test or correcting one you
previously proposed.
Be sure to include assertions in the test that verify any applicable postconditions.
Please also make VERY SURE to clean up after the test, so as to avoid state pollution;
use 'monkeypatch' or 'pytest-mock' if appropriate.
Write as little top-level code as possible, and in particular do not include any top-level code
calling into pytest.main or the test itself.
Respond ONLY with the Python code enclosed in backticks, without any explanation.
```python
{segment.get_excerpt()}
```
""")
        ]


    def error_prompt(self, segment: CodeSegment, error: str) -> list[dict] | None:
        if "error" in self.templates:
            return [mk_message(self._render("error", self.templates["error"], error=error))]
        return [mk_message(f"""\
Executing the test yields an error, shown below.
Modify or rewrite the test to correct it; respond only with the complete Python code in backticks.
Use the get_info tool function as necessary.

{error}""")
        ]


    def get_info(self, ctx: CodeSegment, name: str) -> str:
        """
        {
            "name": "get_info",
            "description": "Returns information about a symbol.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "class, function or method name, as in 'f' for function f or 'C.foo' for method foo in class C."
                    }
                },
                "required": ["name"]
            }
        }
        """

        if info := codeinfo.get_info(codeinfo.parse_file(ctx.path), name, line=ctx.begin):
            return "\"...\" below indicates omitted code.\n\n" + info

        return f"Unable to obtain information on {name}."


    def get_functions(self) -> list[Callable]:
        return [self.get_info]
