import json
import os
from pathlib import Path

import coverup.coverup as engine
from coverup.prompt.gpt_v2 import GptV2Prompter
from coverup.prompt.prompter import mk_message
from project_setup import prepare_project

if project_root := os.environ.get("PROMPTOPT_PROJECT_ROOT"):
    setup_report, setup_environment = prepare_project(
        Path(project_root),
        Path(os.environ["PROMPTOPT_PACKAGE_DIR"]),
        os.environ.copy(),
        metadata_site=Path(os.environ["PROMPTOPT_SETUP_SITE"]),
    )
    os.environ.update(setup_environment)
    Path(os.environ["PROMPTOPT_SETUP_REPORT"]).write_text(
        json.dumps(setup_report.as_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

with open(os.environ["PROMPTOPT_PROMPT_FILE"], encoding="utf-8") as file:
    prompt = json.load(file)
targets = set(json.loads(os.environ.get("PROMPTOPT_TARGET_SYMBOLS", "[]")))


class VersionedPrompter(GptV2Prompter):
    def initial_prompt(self, segment):
        filename = segment.path.relative_to(self.args.src_base_dir)
        return [
            mk_message(
                prompt["initial"].format(
                    filename=filename,
                    coverage_targets=segment.lines_branches_missing_do(),
                    source_excerpt=segment.get_excerpt(),
                )
            )
        ]

    def error_prompt(self, segment, error):
        del segment
        return [mk_message(prompt["error"].format(error=error))]


engine.prompter_registry["gpt-v2"] = VersionedPrompter
original_missing = engine.get_missing_coverage


def selected_missing(*args, **kwargs):
    segments = original_missing(*args, **kwargs)
    if not targets:
        return segments
    return [
        segment
        for segment in segments
        if segment.name in targets or any(segment.name.endswith(f".{name}") for name in targets)
    ]


engine.get_missing_coverage = selected_missing
raise SystemExit(engine.main())
