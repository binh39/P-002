from __future__ import annotations

import io
import json
import zipfile
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path, PurePosixPath

from src.modules.analysis.analyzer import AnalysisResult, analyze_zip
from src.modules.analysis.schemas import ProjectFunctionRecord
from src.modules.projects.schemas import (
    CoverageSettings,
    ProjectRecord,
    ProjectSettings,
    ProjectStatus,
    RuntimeSettings,
    TestSettings,
)

SAMPLE_PROJECT_PREFIX = "sample:"
_SNAPSHOT_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_IGNORED_PARTS = {
    ".git",
    ".venv",
    ".promptopt-site",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
}


@dataclass(frozen=True, slots=True)
class SampleDefinition:
    slug: str
    name: str
    description: str
    commit: str
    source_directory: str
    python_file_count: int
    function_count: int
    statement_count: int
    branch_count: int
    required_imports: tuple[str, ...]
    excluded_source_parts: tuple[str, ...]

    @property
    def project_id(self) -> str:
        return f"{SAMPLE_PROJECT_PREFIX}{self.slug}"


SAMPLE_DEFINITIONS = (
    SampleDefinition(
        slug="isort",
        name="isort",
        description="Python import sorting library; compact sample for fast experiments.",
        commit="0a09c78",
        source_directory="isort",
        python_file_count=23,
        function_count=226,
        statement_count=3344,
        branch_count=970,
        required_imports=("tomli",),
        excluded_source_parts=("_vendored", "deprecated"),
    ),
    SampleDefinition(
        slug="mimesis",
        name="mimesis",
        description="Fake-data generator with a broad provider-oriented API surface.",
        commit="56427956",
        source_directory="mimesis",
        python_file_count=33,
        function_count=389,
        statement_count=2027,
        branch_count=249,
        required_imports=(),
        excluded_source_parts=(),
    ),
    SampleDefinition(
        slug="mlxtend",
        name="mlxtend",
        description="Machine-learning extensions with statement and branch-heavy targets.",
        commit="29e2fc4a",
        source_directory="mlxtend",
        python_file_count=101,
        function_count=411,
        statement_count=5443,
        branch_count=1202,
        required_imports=("numpy", "scipy", "pandas", "sklearn", "matplotlib", "joblib"),
        excluded_source_parts=(),
    ),
    SampleDefinition(
        slug="typesystem",
        name="typesystem",
        description="Typed validation and form library with a small, focused codebase.",
        commit="e887641",
        source_directory="typesystem",
        python_file_count=12,
        function_count=176,
        statement_count=1448,
        branch_count=357,
        required_imports=("jinja2", "yaml"),
        excluded_source_parts=(),
    ),
)


class SampleProjectCatalog:
    """Read-only sample projects shipped with the API image.

    Samples never create upload, project, or function documents. Their stable metadata and
    analyzed functions are reconstructed from the bundled source on each API instance and cached
    in memory. Experiment and run records can safely refer to the stable ``sample:<slug>`` IDs.
    """

    def __init__(self, root: str | Path, max_python_files: int, max_uncompressed_bytes: int):
        self.root = Path(root).resolve()
        self.max_python_files = max_python_files
        self.max_uncompressed_bytes = max_uncompressed_bytes
        self._definitions = {item.project_id: item for item in SAMPLE_DEFINITIONS}

    def contains(self, project_id: str) -> bool:
        return project_id in self._definitions

    def list(self, owner_id: str) -> list[ProjectRecord]:
        return [self._record(item, owner_id) for item in SAMPLE_DEFINITIONS]

    def get(self, project_id: str, owner_id: str) -> ProjectRecord | None:
        definition = self._definitions.get(project_id)
        return self._record(definition, owner_id) if definition else None

    def archive(self, project_id: str) -> bytes:
        return self._snapshot(project_id)[0]

    def functions(self, project_id: str) -> list[ProjectFunctionRecord]:
        return list(self._snapshot(project_id)[1].functions)

    def function(self, project_id: str, function_id: str) -> ProjectFunctionRecord | None:
        return next((item for item in self.functions(project_id) if item.id == function_id), None)

    @lru_cache(maxsize=4)
    def _snapshot(self, project_id: str) -> tuple[bytes, AnalysisResult]:
        definition = self._definitions.get(project_id)
        if definition is None:
            raise KeyError(f"Unknown sample project: {project_id}")
        repository = (self.root / definition.slug).resolve()
        if self.root not in repository.parents or not repository.is_dir():
            raise RuntimeError(f"Bundled sample repository is missing: {definition.slug}")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(repository.rglob("*")):
                if not path.is_file() or any(part in _IGNORED_PARTS for part in path.parts):
                    continue
                bundle.write(path, path.relative_to(repository).as_posix())
            bundle.writestr(
                ".promptopt/setup.json",
                json.dumps(
                    {
                        "distribution_name": definition.slug,
                        "import_name": definition.source_directory,
                        "required_imports": definition.required_imports,
                    },
                    separators=(",", ":"),
                ),
            )
        archive = buffer.getvalue()
        analyzed = analyze_zip(
            project_id,
            archive,
            self.max_python_files,
            self.max_uncompressed_bytes,
        )
        source_prefix = f"{definition.source_directory}/"
        functions = [
            item
            for item in analyzed.functions
            if item.file.startswith(source_prefix)
            and "/tests/" not in f"/{item.file}/"
            and not any(part in PurePosixPath(item.file).parts for part in definition.excluded_source_parts)
        ]
        symbol_counts = Counter(item.qualified_name for item in functions)
        functions = [item for item in functions if symbol_counts[item.qualified_name] == 1]
        source_files = {item.file for item in functions}
        filtered = AnalysisResult(
            functions=functions,
            python_file_count=len(source_files),
            statement_count=sum(item.statements for item in functions),
            branch_count=sum(item.branches for item in functions),
            warning_count=analyzed.warning_count,
        )
        return archive, filtered

    def _record(self, definition: SampleDefinition, owner_id: str) -> ProjectRecord:
        settings = ProjectSettings(
            runtime=RuntimeSettings(
                python_version="3.12",
                runtime_image="promptopt-gepa-runner",
                source_directory=definition.source_directory,
            ),
            tests=TestSettings(test_directory="tests", test_command="pytest -q"),
            coverage=CoverageSettings(
                include_pattern=f"{definition.source_directory}/**/*.py",
                source_package=definition.source_directory,
            ),
        )
        return ProjectRecord(
            id=definition.project_id,
            owner_id=owner_id,
            name=definition.name,
            description=definition.description,
            upload_id=f"sample:{definition.slug}",
            object_name=f"sample://{definition.slug}",
            branch="sample-snapshot",
            commit=definition.commit,
            status=ProjectStatus.READY,
            settings=settings,
            python_file_count=definition.python_file_count,
            function_count=definition.function_count,
            statement_count=definition.statement_count,
            branch_count=definition.branch_count,
            analyzed_at=_SNAPSHOT_TIME,
            created_at=_SNAPSHOT_TIME,
            updated_at=_SNAPSHOT_TIME,
        )
