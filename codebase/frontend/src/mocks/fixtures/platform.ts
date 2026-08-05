export type ProjectStatus = "ready" | "warning" | "analyzing";

export interface PythonProject {
  id: string;
  name: string;
  description: string;
  python: string;
  commit: string;
  branch: string;
  files: number;
  functions: number;
  statements: number;
  branches: number;
  status: ProjectStatus;
  analyzedAt: string;
  testCommand: string;
  sourceDir: string;
  testDir: string;
}

export const pythonProjects: PythonProject[] = [
  {
    id: "isort",
    name: "isort",
    description: "Python import formatter with rich configuration and sorting rules.",
    python: "3.11",
    commit: "9262aa8",
    branch: "main",
    files: 42,
    functions: 186,
    statements: 4823,
    branches: 1146,
    status: "ready",
    analyzedAt: "5 minutes ago",
    testCommand: "pytest -q tests",
    sourceDir: "isort/",
    testDir: "tests/",
  },
  {
    id: "httpx",
    name: "httpx",
    description: "Async-capable HTTP client used to evaluate I/O-heavy functions.",
    python: "3.11",
    commit: "3bd19fe",
    branch: "master",
    files: 67,
    functions: 294,
    statements: 7610,
    branches: 1862,
    status: "warning",
    analyzedAt: "Yesterday",
    testCommand: "pytest -q tests --disable-warnings",
    sourceDir: "httpx/",
    testDir: "tests/",
  },
  {
    id: "attrs",
    name: "attrs",
    description: "Class helpers with decorators, validators and edge-case branches.",
    python: "3.12",
    commit: "bd8f611",
    branch: "main",
    files: 31,
    functions: 128,
    statements: 3184,
    branches: 792,
    status: "ready",
    analyzedAt: "2 hours ago",
    testCommand: "pytest -q tests --timeout=30",
    sourceDir: "src/attr/",
    testDir: "tests/",
  },
];

export const projectFunctions = [
  {
    id: "fn-1",
    project: "isort",
    file: "isort/api.py",
    className: "",
    name: "sort_code_string",
    lines: "34–82",
    loc: 49,
    statements: 31,
    branches: 12,
    status: "Valid",
  },
  {
    id: "fn-2",
    project: "isort",
    file: "isort/core.py",
    className: "FindersManager",
    name: "find",
    lines: "201–278",
    loc: 78,
    statements: 54,
    branches: 24,
    status: "Valid",
  },
  {
    id: "fn-3",
    project: "isort",
    file: "isort/settings.py",
    className: "Config",
    name: "__init__",
    lines: "307–425",
    loc: 119,
    statements: 81,
    branches: 31,
    status: "Valid",
  },
  {
    id: "fn-4",
    project: "httpx",
    file: "httpx/_client.py",
    className: "Client",
    name: "request",
    lines: "786–921",
    loc: 136,
    statements: 92,
    branches: 38,
    status: "Valid",
  },
  {
    id: "fn-5",
    project: "httpx",
    file: "httpx/_urls.py",
    className: "URL",
    name: "copy_with",
    lines: "340–401",
    loc: 62,
    statements: 41,
    branches: 18,
    status: "Warning",
  },
  {
    id: "fn-6",
    project: "attrs",
    file: "attr/_make.py",
    className: "",
    name: "fields",
    lines: "1842–1906",
    loc: 65,
    statements: 44,
    branches: 17,
    status: "Valid",
  },
  {
    id: "fn-7",
    project: "attrs",
    file: "attr/validators.py",
    className: "_DeepIterable",
    name: "__call__",
    lines: "335–392",
    loc: 58,
    statements: 37,
    branches: 22,
    status: "Valid",
  },
];

export const experiments = [
  {
    id: "EXP-2408",
    name: "GEPA branch optimization",
    projects: "isort + attrs",
    dataset: "DS-104",
    model: "Gemini 2.5 Pro",
    status: "Running",
    score: "0.74",
    statement: "81.2%",
    branch: "68.4%",
    updated: "3 min ago",
  },
  {
    id: "EXP-2407",
    name: "Baseline vs optimized v4",
    projects: "isort",
    dataset: "DS-103",
    model: "Gemini 2.5 Flash",
    status: "Completed",
    score: "0.82",
    statement: "88.6%",
    branch: "76.8%",
    updated: "Today, 10:42",
  },
  {
    id: "EXP-2406",
    name: "HTTP client edge cases",
    projects: "httpx",
    dataset: "DS-102",
    model: "Gemini 2.5 Pro",
    status: "Failed",
    score: "—",
    statement: "—",
    branch: "—",
    updated: "Yesterday",
  },
  {
    id: "EXP-2405",
    name: "Random seed validation",
    projects: "attrs",
    dataset: "DS-101",
    model: "Gemini 2.5 Flash",
    status: "Draft",
    score: "—",
    statement: "—",
    branch: "—",
    updated: "Aug 2",
  },
];

export const datasets = [
  {
    id: "DS-104",
    name: "High branch multi-project",
    projects: "isort, attrs",
    method: "Highest branch",
    train: 60,
    validation: 20,
    test: 20,
    seed: 839201,
    status: "In use",
    created: "Today, 14:20",
  },
  {
    id: "DS-103",
    name: "isort stable benchmark",
    projects: "isort",
    method: "Highest statement",
    train: 40,
    validation: 10,
    test: 20,
    seed: 291104,
    status: "Ready",
    created: "Aug 4",
  },
  {
    id: "DS-102",
    name: "httpx random sample",
    projects: "httpx",
    method: "Random",
    train: 80,
    validation: 20,
    test: 30,
    seed: 74822,
    status: "Ready",
    created: "Aug 3",
  },
];

export const sourcePreview = `def sort_code_string(code: str, extension: str = "py", **config_kwargs: Any) -> str:
    """Sort imports in a Python code string."""
    config = Config(extension=extension, **config_kwargs)
    if not code.strip():
        return code

    try:
        return sort_stream(StringIO(code), config=config)
    except ExistingSyntaxErrors:
        if config.atomic:
            raise
        return code`;
