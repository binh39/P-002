import { useQuery } from "@tanstack/react-query";
import { type ReactNode, useState } from "react";
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

function TestSuiteSettings({ run }: { run: TestGenerationRun }) {
  const values: Array<[string, string]> = [
    ["Environment", run.runtimeEnvironmentId || "Cloud Run isolated runner"],
    ["Function selection", samplingLabels[run.samplingMethod]],
    ["Functions", String(run.targetIds.length)],
    ["Random seed", run.samplingMethod === "random" ? String(run.randomSeed) : "None Available"],
    ["Model", run.model],
    [
      "CoverUp",
      `${run.maxAttempts} attempts · ${run.repeatTests} repeats · concurrency ${run.maxConcurrency}`,
    ],
    ["Rate limit", run.rateLimit === null ? "Default" : `${run.rateLimit} requests/min`],
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

function PythonCode({ content, label }: { content: string; label: string }) {
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
  return (
    <pre className="test-case-code" aria-label={label}>
      <code>{nodes}</code>
    </pre>
  );
}

export default function TestCaseDetail() {
  const [, params] = useRoute("/test-cases/:runId");
  const [, navigate] = useLocation();
  const { testGeneration } = useRepositories();
  const runId = params?.runId ?? "";
  const [selectedTestAlias, setSelectedTestAlias] = useState<string | null>(null);
  const [selectedSourceAlias, setSelectedSourceAlias] = useState<string | null>(null);
  const query = useQuery({
    queryKey: ["test-generation-runs", runId],
    queryFn: ({ signal }) => testGeneration.get(runId, signal),
    enabled: runId !== "",
    refetchInterval: (current) =>
      current.state.data && activeStatuses.includes(current.state.data.status) ? 3_000 : false,
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
  const selectedSource =
    sourceFiles.find((artifact) => artifact.alias === selectedSourceAlias) ?? sourceFiles[0];
  const testQuery = useQuery({
    queryKey: ["test-generation-runs", runId, "test", selectedTest?.alias],
    queryFn: ({ signal }) =>
      testGeneration.getTextArtifact(runId, selectedTest?.alias ?? "", signal),
    enabled: selectedTest !== undefined && runId !== "",
    retry: 1,
  });
  const sourceQuery = useQuery({
    queryKey: ["test-generation-runs", runId, "source", selectedSource?.alias],
    queryFn: ({ signal }) =>
      testGeneration.getTextArtifact(runId, selectedSource?.alias ?? "", signal),
    enabled: selectedSource !== undefined && runId !== "",
    retry: 1,
  });

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
  return (
    <div className="platform-page test-case-detail-page">
      <button className="back-link" onClick={() => navigate("/test-cases")}>
        ← Test Suites
      </button>
      <PageHeader
        eyebrow={`Experiment · ${run.experimentId}`}
        title={run.name}
        description={`${run.promptRole === "baseline" ? "Baseline" : "Final"} prompt · Experiment ${run.experimentId}`}
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
      <section className="platform-card test-case-explorer">
        <aside className="test-case-file-list">
          <div className="card-heading">
            <h2>Test cases</h2>
          </div>
          {manifestQuery.isPending && <p role="status">Loading generated tests…</p>}
          {manifestQuery.isError && (
            <p className="inline-validation-error">Generated tests are unavailable for this run.</p>
          )}
          {!manifestQuery.isPending && !manifestQuery.isError && generatedTests.length === 0 && (
            <p className="muted-cell">No generated Python test files were recorded.</p>
          )}
          <div className="test-case-file-buttons">
            {generatedTests.map((artifact) => (
              <button
                type="button"
                key={artifact.alias}
                className={selectedTest?.alias === artifact.alias ? "is-selected" : ""}
                title={artifact.path}
                onClick={() => setSelectedTestAlias(artifact.alias)}
              >
                {fileName(artifact.path)}
              </button>
            ))}
          </div>
        </aside>
        <section className="test-case-code-panel">
          <div className="card-heading">
            <h2>Source code</h2>
            {sourceFiles.length > 1 && (
              <select
                aria-label="Select source file"
                value={selectedSource?.alias ?? ""}
                onChange={(event) => setSelectedSourceAlias(event.target.value)}
              >
                {sourceFiles.map((artifact) => (
                  <option key={artifact.alias} value={artifact.alias}>
                    {artifact.path}
                  </option>
                ))}
              </select>
            )}
          </div>
          {sourceFiles.length === 0 ? (
            <p className="muted-cell">
              Source code was not stored for this historical run. Generate a new suite after
              deployment to view it here.
            </p>
          ) : sourceQuery.isPending ? (
            <p role="status">Loading source…</p>
          ) : sourceQuery.isError ? (
            <p className="inline-validation-error">Source code could not be loaded.</p>
          ) : sourceQuery.data ? (
            <PythonCode content={sourceQuery.data.content} label="Source code" />
          ) : null}
        </section>
        <section className="test-case-code-panel">
          <div className="card-heading">
            <h2>Generated test</h2>
          </div>
          {!selectedTest ? (
            <p className="muted-cell">Select a generated test file.</p>
          ) : testQuery.isPending ? (
            <p role="status">Loading test…</p>
          ) : testQuery.isError ? (
            <p className="inline-validation-error">Generated test could not be loaded.</p>
          ) : testQuery.data ? (
            <PythonCode content={testQuery.data.content} label="Generated test code" />
          ) : null}
        </section>
      </section>
      <TestSuiteSettings run={run} />
    </div>
  );
}
