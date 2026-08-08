import json
import os
from pathlib import Path

import coverup.coverup as engine
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

raise SystemExit(engine.main())
