import { useQueries, useQuery } from "@tanstack/react-query";
import {
  ChevronDown,
  ChevronRight,
  Download,
  Maximize2,
  Minimize2,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { type ReactNode, useEffect, useRef, useState } from "react";
import { useLocation, useRoute } from "wouter";

import { useRepositories } from "@/app/providers";
import { PageHeader, StatCard, StatusBadge } from "@/components/PlatformUI";
import type { TestGenerationRun, TestGenerationStatus } from "@/domain/experiments";

const activeStatuses: TestGenerationStatus[] = [
  "queued",
  "preparing",
  "generating",
  "running_tests",
];
const pythonKeywords = new Set([
  "and",
  "as",
  "assert",
  "async",
  "await",
  "break",
  "class",
  "continue",
  "def",
  "del",
  "elif",
  "else",
  "except",
  "False",
  "finally",
  "for",
  "from",
  "if",
  "import",
  "in",
  "is",
  "lambda",
  "None",
  "not",
  "or",
  "pass",
  "raise",
  "return",
  "True",
  "try",
  "while",
  "with",
  "yield",
]);

type IndexedArtifact = {
  id: string;
  kind: "generated_test" | "source" | "coverage";
  path: string;
  alias: string;
};

function indexedArtifacts(manifest: Record<string, unknown>): IndexedArtifact[] {
  const artifacts = manifest.artifacts;
  if (!artifacts || typeof artifacts !== "object") return [];
  const files = (artifacts as Record<string, unknown>).files;
  if (!Array.isArray(files)) return [];
  return files.flatMap((file) => {
    if (!file || typeof file !== "object") return [];
    const entry = file as Record<string, unknown>;
    const id = entry.id;
    const kind = entry.kind;
    const path = entry.path;
    if (
      typeof id !== "string" ||
      typeof path !== "string" ||
      (kind !== "generated_test" && kind !== "source" && kind !== "coverage") ||
      !/^[a-z0-9-]{1,80}$/.test(id)
    )
      return [];
    return [{ id, kind, path, alias: `file-${id}` }];
  });
}

function percentage(value: number | null) {
  return value === null ? "—" : `${(value * 100).toFixed(1)}%`;
}
function formatStatus(status: TestGenerationStatus) {
  return status.replace(/_/g, " ").replace(/^./, (char) => char.toUpperCase());
}
function statusTone(status: TestGenerationStatus) {
  if (status === "completed") return "success" as const;
  if (["failed", "cancelled", "timed_out"].includes(status)) return "danger" as const;
  if (status === "partial") return "warning" as const;
  return "info" as const;
}
function formatCost(value: number) {
  return new Intl.NumberFormat(undefined, { style: "currency", currency: "USD" }).format(value);
}
function fileName(path: string) {
  return path.split("/").at(-1) ?? path;
}
function displaySourcePath(path: string) {
  const normalized = path.replace(/\\/g, "/").replace(/^source\//, "");
  const duplicatedDirectory = normalized.match(/^([^/]+)\/\1\//);
  return duplicatedDirectory ? normalized.slice(duplicatedDirectory[1].length + 1) : normalized;
}

function progressWidth(value: number | null) {
  return `${Math.round(Math.max(0, Math.min(1, value ?? 0)) * 100)}%`;
}

function combinedCoverageScore(statement: number | null, branch: number | null) {
  if (statement === null || branch === null) return null;
  return (statement + branch) / 2;
}

function MetricBar({
  value,
  tone,
}: {
  value: number | null;
  tone: "final" | "statement" | "branch";
}) {
  return (
    <span className={`prompt-registry-metric-bar is-${tone}`} aria-hidden="true">
      <span style={{ width: progressWidth(value) }} />
    </span>
  );
}

function TestSuiteMetrics({
  targetScore,
  projectStatementCoverage,
  projectBranchCoverage,
  targetStatementCoverage,
  targetBranchCoverage,
}: {
  targetScore: number | null;
  projectStatementCoverage: number | null;
  projectBranchCoverage: number | null;
  targetStatementCoverage: number | null;
  targetBranchCoverage: number | null;
}) {
  const projectScore = combinedCoverageScore(projectStatementCoverage, projectBranchCoverage);
  return (
    <section className="platform-card prompt-registry-summary test-suite-summary">
      <div className="prompt-registry-metric-comparison">
        <section className="prompt-registry-metric-panel is-final">
          <h2>Project Coverage</h2>
          <div className="prompt-registry-primary-score">
            <span>Score</span>
            <strong>{percentage(projectScore)}</strong>
          </div>
          <MetricBar value={projectScore} tone="final" />
          <div className="prompt-registry-coverage-list">
            <div>
              <span>Statement coverage</span>
              <strong>{percentage(projectStatementCoverage)}</strong>
              <MetricBar value={projectStatementCoverage} tone="statement" />
            </div>
            <div>
              <span>Branch coverage</span>
              <strong>{percentage(projectBranchCoverage)}</strong>
              <MetricBar value={projectBranchCoverage} tone="branch" />
            </div>
          </div>
        </section>
        <section className="prompt-registry-metric-panel is-final">
          <h2>Target Coverage</h2>
          <div className="prompt-registry-primary-score">
            <span>Score</span>
            <strong>{percentage(targetScore)}</strong>
          </div>
          <MetricBar value={targetScore} tone="final" />
          <div className="prompt-registry-coverage-list">
            <div>
              <span>Statement coverage</span>
              <strong>{percentage(targetStatementCoverage)}</strong>
              <MetricBar value={targetStatementCoverage} tone="statement" />
            </div>
            <div>
              <span>Branch coverage</span>
              <strong>{percentage(targetBranchCoverage)}</strong>
              <MetricBar value={targetBranchCoverage} tone="branch" />
            </div>
          </div>
        </section>
      </div>
    </section>
  );
}

const samplingLabels: Record<TestGenerationRun["samplingMethod"], string> = {
  random: "Random",
  most_branches: "Most branches",
  most_statements: "Most statements",
  manual: "Manual selection",
};

function TestSuiteSettings({
  run,
  experimentName,
  projectNames,
}: {
  run: TestGenerationRun;
  experimentName: string;
  projectNames: string[];
}) {
  const prompt = run.promptRole === "baseline" ? "Baseline Prompt" : "Final Prompt";
  const values: Array<[string, string]> = [
    ["Test Suite", run.name],
    ["Experiment", experimentName],
    ["Prompt", prompt],
    ["Projects", projectNames.join(", ") || "Prompt experiment projects"],
    ["Function selection", samplingLabels[run.samplingMethod]],
    ["Functions", String(run.targetIds.length)],
    ["Random seed", run.samplingMethod === "random" ? String(run.randomSeed) : "None Available"],
    ["Model", run.model],
    ["Scope", run.scope],
    [
      "CoverUp",
      `${run.maxAttempts} attempts · ${run.repeatTests} repeats · concurrency ${run.maxConcurrency}`,
    ],
    ["Rate limit", run.rateLimit === null ? "Default" : `${run.rateLimit} requests/min`],
    ["Cost ceiling", run.costCeilingUsd === null ? "Not set" : `$${run.costCeilingUsd.toFixed(2)}`],
    ["Runner protocol", `v${run.runnerProtocolVersion}`],
  ];
  return (
    <section className="platform-card prompt-registry-settings-card">
      <div className="card-heading">
        <h2>Test Suite Settings</h2>
      </div>
      <dl className="definition-list prompt-registry-settings-list">
        {values.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd title={value}>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

type TestDefinition = {
  key: string;
  name: string;
  label: string;
  startLine: number;
  endLine: number;
  artifact: IndexedArtifact;
};

type SourceDefinition = {
  name: string;
  startLine: number;
  endLine: number;
  artifact: IndexedArtifact;
};

function readableTestName(name: string) {
  return name
    .replace(/^test_/, "")
    .replace(/_/g, " ")
    .replace(/\bstr\b/g, "string");
}

function testDefinitions(artifact: IndexedArtifact, content: string): TestDefinition[] {
  const lines = content.split("\n");
  const starts: Array<{ name: string; line: number; indent: number }> = [];
  lines.forEach((line, index) => {
    const match = line.match(/^(\s*)(?:async\s+)?def\s+(test_[A-Za-z0-9_]+)\s*\(/);
    if (match) starts.push({ name: match[2], line: index + 1, indent: match[1].length });
  });
  return starts.map((item, index) => {
    const next = starts.slice(index + 1).find((candidate) => candidate.indent <= item.indent);
    return {
      key: `${artifact.alias}:${item.name}:${item.line}`,
      name: item.name,
      label: readableTestName(item.name),
      startLine: item.line,
      endLine: next ? next.line - 1 : lines.length,
      artifact,
    };
  });
}

function sourceDefinitions(artifact: IndexedArtifact, content: string): SourceDefinition[] {
  const lines = content.split("\n");
  const starts: Array<{ name: string; line: number; indent: number }> = [];
  lines.forEach((line, index) => {
    const match = line.match(/^(\s*)(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(/);
    if (match) starts.push({ name: match[2], line: index + 1, indent: match[1].length });
  });
  return starts.map((item, index) => {
    const next = starts.slice(index + 1).find((candidate) => candidate.indent <= item.indent);
    return {
      name: item.name,
      startLine: item.line,
      endLine: next ? next.line - 1 : lines.length,
      artifact,
    };
  });
}

function sourceDefinitionForTest(
  test: TestDefinition | undefined,
  testContent: string | undefined,
  sources: Array<{ artifact: IndexedArtifact; content: string }>,
) {
  if (!test || !testContent) return undefined;
  const testBody = testContent
    .split("\n")
    .slice(test.startLine - 1, test.endLine)
    .join("\n");
  const normalizedTestName = test.name.replace(/^test_/, "");
  const candidates = sources
    .flatMap(({ artifact, content }) => sourceDefinitions(artifact, content))
    .filter((definition) => {
      if (definition.name.startsWith("test_")) return false;
      const namePattern = new RegExp(
        `(^|_)${definition.name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(_|$)`,
      );
      const bodyPattern = new RegExp(
        `\\b${definition.name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`,
      );
      return namePattern.test(normalizedTestName) && bodyPattern.test(testBody);
    })
    .sort((left, right) => right.name.length - left.name.length);
  if (candidates.length === 0) return undefined;
  if (candidates.length > 1 && candidates[0].name.length === candidates[1].name.length)
    return undefined;
  return candidates[0];
}

function highlightedPython(content: string) {
  const pattern =
    /(#.*$)|((?:[rubf]|br|rf)?(?:"""[\s\S]*?"""|'''[\s\S]*?'''|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'))|(\b[A-Za-z_][A-Za-z0-9_]*\b)|(\b\d+(?:\.\d+)?\b)/gim;
  const nodes: ReactNode[] = [];
  let cursor = 0;
  for (const match of content.matchAll(pattern)) {
    const index = match.index ?? 0;
    if (index > cursor) nodes.push(content.slice(cursor, index));
    const token = match[0];
    const className = match[1]
      ? "syntax-comment"
      : match[2]
        ? "syntax-string"
        : match[3] && pythonKeywords.has(token)
          ? "syntax-keyword"
          : match[4]
            ? "syntax-number"
            : undefined;
    nodes.push(
      className ? (
        <span className={className} key={`${index}-${token}`}>
          {token}
        </span>
      ) : (
        token
      ),
    );
    cursor = index + token.length;
  }
  if (cursor < content.length) nodes.push(content.slice(cursor));
  return nodes;
}

function PythonCode({
  content,
  label,
  highlight,
  scrollKey,
}: {
  content: string;
  label: string;
  highlight?: { start: number; end: number; preview?: boolean };
  scrollKey?: string;
}) {
  const selectedLineRef = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const selectedLine = selectedLineRef.current;
    const codeViewport = selectedLine?.closest(".test-case-code");
    if (!selectedLine || !(codeViewport instanceof HTMLElement) || !scrollKey) return;
    const selectedLineBounds = selectedLine.getBoundingClientRect();
    const viewportBounds = codeViewport.getBoundingClientRect();
    codeViewport.scrollTo({
      top: Math.max(
        0,
        codeViewport.scrollTop +
          selectedLineBounds.top -
          viewportBounds.top -
          codeViewport.clientHeight * 0.32 +
          100,
      ),
      behavior: "smooth",
    });
  }, [scrollKey]);
  return (
    <pre className="test-case-code" aria-label={label}>
      <code>
        {content.split("\n").map((line, index) => {
          const lineNumber = index + 1;
          const isHighlighted =
            highlight !== undefined && lineNumber >= highlight.start && lineNumber <= highlight.end;
          return (
            <span
              className={`test-case-code-line${isHighlighted ? " is-highlighted" : ""}${isHighlighted && highlight.preview ? " is-preview" : ""}`}
              key={lineNumber}
              ref={lineNumber === highlight?.start ? selectedLineRef : undefined}
            >
              <span className="test-case-line-number">{lineNumber}</span>
              <span className="test-case-line-content">{highlightedPython(line) || " "}</span>
            </span>
          );
        })}
      </code>
    </pre>
  );
}

export default function TestCaseDetail() {
  const [, params] = useRoute("/test-cases/:runId");
  const [, navigate] = useLocation();
  const { experiments, projects, testGeneration } = useRepositories();
  const runId = params?.runId ?? "";
  const [selectedTestAlias, setSelectedTestAlias] = useState<string | null>(null);
  const [selectedSourceAlias, setSelectedSourceAlias] = useState<string | null>(null);
  const [selectedTestKey, setSelectedTestKey] = useState<string | null>(null);
  const [testSearch, setTestSearch] = useState("");
  const [explorerCollapsed, setExplorerCollapsed] = useState(false);
  const [collapsedModules, setCollapsedModules] = useState<Set<string>>(() => new Set());
  const [viewerExpanded, setViewerExpanded] = useState(false);
  const [downloadPending, setDownloadPending] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  useEffect(() => {
    if (!viewerExpanded) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setViewerExpanded(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [viewerExpanded]);
  const query = useQuery({
    queryKey: ["test-generation-runs", runId],
    queryFn: ({ signal }) => testGeneration.get(runId, signal),
    enabled: runId !== "",
    refetchInterval: (current) =>
      current.state.data && activeStatuses.includes(current.state.data.status) ? 3_000 : false,
  });
  const experimentQuery = useQuery({
    queryKey: ["experiments", "test-generation", query.data?.experimentId],
    queryFn: ({ signal }) => experiments.get(query.data?.experimentId ?? "", signal),
    enabled: query.data?.experimentId !== undefined,
  });
  const projectQueries = useQuery({
    queryKey: ["projects", "test-generation", runId],
    queryFn: async ({ signal }) => {
      const [imported, samples] = await Promise.all([
        projects.list(signal),
        projects.listSamples(signal),
      ]);
      return [...imported, ...samples];
    },
    enabled: query.data !== undefined,
  });
  const manifestQuery = useQuery({
    queryKey: ["test-generation-runs", runId, "manifest"],
    queryFn: ({ signal }) => testGeneration.getManifest(runId, signal),
    enabled:
      runId !== "" && query.data !== undefined && !activeStatuses.includes(query.data.status),
    retry: 1,
  });
  const indexed = manifestQuery.data ? indexedArtifacts(manifestQuery.data) : [];
  const generatedTests = indexed.filter((artifact) => artifact.kind === "generated_test");
  const sourceFiles = indexed.filter((artifact) => artifact.kind === "source");
  const selectedTest =
    generatedTests.find((artifact) => artifact.alias === selectedTestAlias) ?? generatedTests[0];
  const testArtifactQueries = useQueries({
    queries: generatedTests.map((artifact) => ({
      queryKey: ["test-generation-runs", runId, "test", artifact.alias],
      queryFn: ({ signal }: { signal: AbortSignal }) =>
        testGeneration.getTextArtifact(runId, artifact.alias, signal),
      enabled: runId !== "",
      retry: 1,
    })),
  });
  const generatedDefinitions = generatedTests.flatMap((artifact, index) => {
    const content = testArtifactQueries[index]?.data?.content;
    return content ? testDefinitions(artifact, content) : [];
  });
  const visibleDefinitions = generatedDefinitions.filter((definition) => {
    const term = testSearch.trim().toLowerCase();
    return (
      !term ||
      definition.label.toLowerCase().includes(term) ||
      definition.name.toLowerCase().includes(term) ||
      definition.artifact.path.toLowerCase().includes(term)
    );
  });
  const activeDefinition =
    generatedDefinitions.find((definition) => definition.key === selectedTestKey) ??
    generatedDefinitions[0];
  const focusedTestIndex = activeDefinition
    ? generatedTests.findIndex((artifact) => artifact.alias === activeDefinition.artifact.alias)
    : generatedTests.findIndex((artifact) => artifact.alias === selectedTest?.alias);
  const focusedTestArtifact = activeDefinition?.artifact ?? selectedTest;
  const focusedTestQuery =
    focusedTestIndex >= 0 ? testArtifactQueries[focusedTestIndex] : undefined;
  const sourceArtifactQueries = useQueries({
    queries: sourceFiles.map((artifact) => ({
      queryKey: ["test-generation-runs", runId, "source", artifact.alias],
      queryFn: ({ signal }: { signal: AbortSignal }) =>
        testGeneration.getTextArtifact(runId, artifact.alias, signal),
      enabled: runId !== "",
      retry: 1,
    })),
  });
  const relatedSourceDefinition = sourceDefinitionForTest(
    activeDefinition,
    focusedTestQuery?.data?.content,
    sourceFiles.flatMap((artifact, index) => {
      const content = sourceArtifactQueries[index]?.data?.content;
      return content ? [{ artifact, content }] : [];
    }),
  );
  const selectedSource =
    relatedSourceDefinition?.artifact ??
    sourceFiles.find((artifact) => artifact.alias === selectedSourceAlias) ??
    sourceFiles[0];
  const selectedSourceIndex = sourceFiles.findIndex(
    (artifact) => artifact.alias === selectedSource?.alias,
  );
  const sourceQuery =
    selectedSourceIndex >= 0 ? sourceArtifactQueries[selectedSourceIndex] : undefined;

  if (query.isPending)
    return (
      <div className="page-state" role="status">
        Loading final test run…
      </div>
    );
  if (query.isError || !query.data) {
    return (
      <div className="page-state page-state-error" role="alert">
        <h2>Test run is unavailable</h2>
        <p>
          {query.error instanceof Error
            ? query.error.message
            : "The requested test run was not found."}
        </p>
        <button onClick={() => navigate("/test-cases")}>Back to Test Suites</button>
      </div>
    );
  }

  const run = query.data;
  const experimentName = experimentQuery.data?.name ?? run.experimentId;
  const projectNames = run.projectIds.map(
    (projectId) =>
      projectQueries.data?.find((project) => project.id === projectId)?.name ?? projectId,
  );
  const downloadTestSuite = async () => {
    setDownloadPending(true);
    setDownloadError(null);
    try {
      const blob = await testGeneration.downloadArtifact(run.id, "suite_zip");
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${run.name.replace(/[^a-zA-Z0-9._-]+/g, "-") || "test-suite"}.zip`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      setDownloadError(
        error instanceof Error ? error.message : "Test suite could not be downloaded.",
      );
    } finally {
      setDownloadPending(false);
    }
  };
  return (
    <div className="platform-page test-case-detail-page">
      <button className="back-link" onClick={() => navigate("/test-cases")}>
        ← Test Suites
      </button>
      <PageHeader
        title={run.name}
        description={`${run.promptRole === "baseline" ? "Baseline" : "Final"} prompt · Experiment ${experimentName} · projects ${projectNames.join(", ")}`}
        actions={
          <StatusBadge tone={statusTone(run.status)}>{formatStatus(run.status)}</StatusBadge>
        }
      />
      {run.errorMessage && (
        <section className="prompt-registry-generation-notice is-error" role="alert">
          {run.errorMessage}
        </section>
      )}
      <TestSuiteMetrics
        targetScore={run.metrics.targetScore}
        projectStatementCoverage={run.metrics.projectStatementCoverage}
        projectBranchCoverage={run.metrics.projectBranchCoverage}
        targetStatementCoverage={run.metrics.targetStatementCoverage}
        targetBranchCoverage={run.metrics.targetBranchCoverage}
      />
      <div className="platform-stats-grid test-suite-run-stats">
        <StatCard
          label="Tests"
          value={run.metrics.testCount}
          detail={`${run.metrics.testFileCount} files`}
        />
        <StatCard label="Passed" value={run.metrics.passed ?? "—"} tone="orange" />
        <StatCard label="Failed" value={run.metrics.failed ?? "—"} tone="violet" />
        <StatCard label="Cost" value={formatCost(run.estimatedCostUsd)} tone="green" />
      </div>
      <div className={`test-case-viewer-shell${viewerExpanded ? " is-expanded" : ""}`}>
        <section
          className={`test-case-explorer${explorerCollapsed ? " is-explorer-collapsed" : ""}`}
        >
          <aside className="test-case-file-list" aria-label="Test Explorer">
            <div className="test-explorer-heading">
              {!explorerCollapsed && <h2>Test Explorer</h2>}
              <button
                type="button"
                aria-label={explorerCollapsed ? "Expand Test Explorer" : "Collapse Test Explorer"}
                title={explorerCollapsed ? "Expand Test Explorer" : "Collapse Test Explorer"}
                onClick={() => setExplorerCollapsed((collapsed) => !collapsed)}
              >
                {explorerCollapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
              </button>
            </div>
            {!explorerCollapsed && (
              <input
                className="test-explorer-search"
                type="search"
                placeholder="Search tests..."
                aria-label="Search generated tests"
                value={testSearch}
                onChange={(event) => setTestSearch(event.target.value)}
              />
            )}
            {manifestQuery.isPending && <p role="status">Loading generated tests…</p>}
            {manifestQuery.isError && (
              <p className="inline-validation-error">
                Generated tests are unavailable for this run.
              </p>
            )}
            {!manifestQuery.isPending && !manifestQuery.isError && generatedTests.length === 0 && (
              <p className="muted-cell">No generated Python test files were recorded.</p>
            )}
            {!explorerCollapsed && (
              <div className="test-case-file-buttons">
                {visibleDefinitions.length > 0
                  ? generatedTests.map((artifact, artifactIndex) => {
                      const definitions = visibleDefinitions.filter(
                        (definition) => definition.artifact.alias === artifact.alias,
                      );
                      if (definitions.length === 0) return null;
                      const moduleCollapsed = collapsedModules.has(artifact.alias);
                      return (
                        <div className="test-explorer-group" key={artifact.alias}>
                          <button
                            type="button"
                            className="test-explorer-group-label"
                            title={artifact.path}
                            aria-expanded={!moduleCollapsed}
                            onClick={() =>
                              setCollapsedModules((current) => {
                                const next = new Set(current);
                                if (next.has(artifact.alias)) next.delete(artifact.alias);
                                else next.add(artifact.alias);
                                return next;
                              })
                            }
                          >
                            {moduleCollapsed ? (
                              <ChevronRight aria-hidden="true" size={14} />
                            ) : (
                              <ChevronDown aria-hidden="true" size={14} />
                            )}
                            <strong>Test module {artifactIndex + 1}</strong>
                            <small>{definitions.length}</small>
                          </button>
                          {!moduleCollapsed &&
                            definitions.map((definition) => (
                              <button
                                type="button"
                                key={definition.key}
                                className={
                                  activeDefinition?.key === definition.key ? "is-selected" : ""
                                }
                                title={`${definition.name} · ${artifact.path}`}
                                onClick={() => {
                                  setSelectedTestAlias(artifact.alias);
                                  setSelectedTestKey(definition.key);
                                }}
                              >
                                <span>{definition.label}</span>
                                <small>{definition.name}</small>
                              </button>
                            ))}
                        </div>
                      );
                    })
                  : !manifestQuery.isPending && (
                      <p className="muted-cell">No generated tests match this search.</p>
                    )}
              </div>
            )}
          </aside>
          <section className="test-case-code-panel">
            <div className="card-heading">
              <div>
                <span className="code-panel-kicker">Source</span>
                <h2>{selectedSource ? displaySourcePath(selectedSource.path) : "Source code"}</h2>
              </div>
              {sourceFiles.length > 1 && (
                <select
                  aria-label="Select source file"
                  value={selectedSource?.alias ?? ""}
                  onChange={(event) => setSelectedSourceAlias(event.target.value)}
                >
                  {sourceFiles.map((artifact) => (
                    <option key={artifact.alias} value={artifact.alias}>
                      {displaySourcePath(artifact.path)}
                    </option>
                  ))}
                </select>
              )}
            </div>
            <div className="code-context-bar">
              {relatedSourceDefinition ? (
                <>
                  <strong>{relatedSourceDefinition.name}()</strong>
                  <span>
                    Lines {relatedSourceDefinition.startLine}–{relatedSourceDefinition.endLine}
                  </span>
                  <small>Matched to selected test</small>
                </>
              ) : (
                <>
                  <span>Read-only source</span>
                  <small>No unambiguous function match for this test</small>
                </>
              )}
            </div>
            {sourceFiles.length === 0 ? (
              <p className="muted-cell">
                Source code was not stored for this historical run. Generate a new suite after
                deployment to view it here.
              </p>
            ) : sourceQuery?.isPending ? (
              <p role="status">Loading source…</p>
            ) : sourceQuery?.isError ? (
              <p className="inline-validation-error">Source code could not be loaded.</p>
            ) : sourceQuery?.data ? (
              <PythonCode
                content={sourceQuery.data.content}
                label="Source code"
                highlight={
                  relatedSourceDefinition
                    ? {
                        start: relatedSourceDefinition.startLine,
                        end: relatedSourceDefinition.endLine,
                      }
                    : undefined
                }
                scrollKey={
                  relatedSourceDefinition
                    ? `${activeDefinition?.key}:${relatedSourceDefinition.artifact.alias}:${relatedSourceDefinition.startLine}`
                    : undefined
                }
              />
            ) : null}
          </section>
          <section className="test-case-code-panel">
            <div className="card-heading">
              <div>
                <span className="code-panel-kicker">Generated Test</span>
                <h2>
                  {focusedTestArtifact ? fileName(focusedTestArtifact.path) : "Generated test"}
                </h2>
              </div>
            </div>
            {activeDefinition && (
              <div className="code-context-bar is-related">
                <strong>{activeDefinition.name}()</strong>
                <span>
                  Lines {activeDefinition.startLine}–{activeDefinition.endLine}
                </span>
                <small>Selected test</small>
              </div>
            )}
            {!focusedTestArtifact ? (
              <p className="muted-cell">Select a generated test file.</p>
            ) : focusedTestQuery?.isPending ? (
              <p role="status">Loading test…</p>
            ) : focusedTestQuery?.isError ? (
              <p className="inline-validation-error">Generated test could not be loaded.</p>
            ) : focusedTestQuery?.data ? (
              <PythonCode
                content={focusedTestQuery.data.content}
                label="Generated test code"
                highlight={
                  activeDefinition
                    ? {
                        start: activeDefinition.startLine,
                        end: activeDefinition.endLine,
                      }
                    : undefined
                }
                scrollKey={activeDefinition?.key}
              />
            ) : null}
          </section>
        </section>
        <div className="test-case-viewer-toolbar">
          {downloadError && <span role="alert">{downloadError}</span>}
          <div className="test-case-viewer-actions">
            <button
              type="button"
              aria-label="Download all generated tests"
              title="Download all generated tests"
              disabled={downloadPending || !run.artifactObjects.suite_zip}
              onClick={() => void downloadTestSuite()}
            >
              <Download aria-hidden="true" size={17} />
            </button>
            <button
              type="button"
              aria-label={viewerExpanded ? "Exit expanded viewer" : "Expand test viewer"}
              title={viewerExpanded ? "Exit expanded viewer (Esc)" : "Expand test viewer"}
              onClick={() => setViewerExpanded((expanded) => !expanded)}
            >
              {viewerExpanded ? (
                <Minimize2 aria-hidden="true" size={17} />
              ) : (
                <Maximize2 aria-hidden="true" size={17} />
              )}
            </button>
          </div>
        </div>
      </div>
      <TestSuiteSettings run={run} experimentName={experimentName} projectNames={projectNames} />
    </div>
  );
}
