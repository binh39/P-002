import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useLocation } from "wouter";

import { useRepositories } from "@/app/providers";
import { useAuth } from "@/auth/AuthProvider";
import { IC } from "@/components/Icons";
import { PageHeader, StatusBadge } from "@/components/PlatformUI";
import type { TestGenerationRun, TestGenerationStatus } from "@/domain/experiments";

const activeStatuses: TestGenerationStatus[] = [
  "queued",
  "preparing",
  "generating",
  "running_tests",
];

function percentage(value: number | null) {
  return value === null ? "—" : `${(value * 100).toFixed(1)}%`;
}

function formatStatus(status: TestGenerationStatus) {
  return status.replace(/_/g, " ").replace(/^./, (character) => character.toUpperCase());
}

function statusTone(status: TestGenerationStatus) {
  if (status === "completed") return "success" as const;
  if (["failed", "cancelled", "timed_out"].includes(status)) return "danger" as const;
  if (status === "partial") return "warning" as const;
  return "info" as const;
}

function coverageScore(statement: number | null, branch: number | null) {
  if (statement === null && branch === null) return null;
  if (statement === null) return branch;
  if (branch === null) return statement;
  return (statement + branch) / 2;
}

function coverageWidth(value: number | null) {
  return `${Math.round(Math.max(0, Math.min(1, value ?? 0)) * 100)}%`;
}

function CoverageCell({ value, tone }: { value: number | null; tone: "project" | "target" }) {
  return (
    <div
      className="test-suite-coverage"
      title={value === null ? "Coverage unavailable" : `Coverage ${percentage(value)}`}
    >
      <strong>{percentage(value)}</strong>
      <span className={`test-suite-coverage-bar is-${tone}`} aria-hidden="true">
        <span style={{ width: coverageWidth(value) }} />
      </span>
    </div>
  );
}

function timestamp(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(
    new Date(value),
  );
}

function runMatchesSearch(run: TestGenerationRun, value: string) {
  return [run.name, run.id, run.experimentId, run.projectIds.join(" "), run.model]
    .join(" ")
    .toLowerCase()
    .includes(value);
}

export default function TestCases() {
  const { user } = useAuth();
  const readOnly = user?.role === "prompt_reviewer";
  const [, navigate] = useLocation();
  const { testGeneration } = useRepositories();
  const queryClient = useQueryClient();
  const [deleteTarget, setDeleteTarget] = useState<TestGenerationRun | null>(null);
  const deleteMutation = useMutation({
    mutationFn: (runId: string) => testGeneration.delete(runId),
    onSuccess: async () => {
      setDeleteTarget(null);
      await queryClient.invalidateQueries({ queryKey: ["test-generation-runs"] });
    },
  });
  const [search, setSearch] = useState("");
  const [role, setRole] = useState<"all" | TestGenerationRun["promptRole"]>("all");
  const [status, setStatus] = useState<"all" | TestGenerationStatus>("all");
  const query = useQuery({
    queryKey: ["test-generation-runs"],
    queryFn: ({ signal }) => testGeneration.list(signal),
    refetchInterval: (current) =>
      current.state.data?.items.some((run) => activeStatuses.includes(run.status)) ? 3_000 : false,
  });
  const items = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return (query.data?.items ?? []).filter(
      (run) =>
        (!normalizedSearch || runMatchesSearch(run, normalizedSearch)) &&
        (role === "all" || run.promptRole === role) &&
        (status === "all" || run.status === status),
    );
  }, [query.data?.items, role, search, status]);

  if (query.isPending) {
    return (
      <div className="page-state" role="status">
        Loading final test runs…
      </div>
    );
  }
  if (query.isError) {
    return (
      <div className="page-state page-state-error" role="alert">
        <h2>Test Cases are unavailable</h2>
        <p>
          {query.error instanceof Error ? query.error.message : "An unexpected error occurred."}
        </p>
        <button onClick={() => query.refetch()}>Try again</button>
      </div>
    );
  }

  return (
    <div className="platform-page test-cases-page">
      <PageHeader
        eyebrow="Generated final suites"
        title="Test Suites"
        description="Standalone test suites generated from prompts saved in Prompt Registry."
        actions={
          readOnly ? (
            <span className="status-badge status-info">Read-only</span>
          ) : (
            <button className="primary-button" onClick={() => navigate("/test-suites/new")}>
              Create Test Suites
            </button>
          )
        }
      />
      <section className="platform-card registry-filters">
        <label className="registry-search-field">
          <IC.Search />
          <input
            aria-label="Search test runs"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search run, experiment, project, or model…"
          />
        </label>
        <label className="registry-model-filter">
          <select value={role} onChange={(event) => setRole(event.target.value as typeof role)}>
            <option value="all">All prompts</option>
            <option value="baseline">Baseline</option>
            <option value="optimized">Final</option>
          </select>
        </label>
        <label className="registry-model-filter">
          <select
            value={status}
            onChange={(event) => setStatus(event.target.value as typeof status)}
          >
            <option value="all">All statuses</option>
            {(
              [
                "queued",
                "preparing",
                "generating",
                "running_tests",
                "completed",
                "partial",
                "failed",
                "cancelled",
                "timed_out",
              ] as const
            ).map((item) => (
              <option key={item} value={item}>
                {formatStatus(item)}
              </option>
            ))}
          </select>
        </label>
        <span className="registry-result-count">{items.length} results</span>
      </section>
      <section className="platform-card table-card">
        {items.length === 0 ? (
          <div className="empty-state">
            {query.data.total === 0
              ? "No final test suites yet. Open a completed Prompt Registry entry to generate one."
              : "No test runs match the selected filters."}
          </div>
        ) : (
          <div className="table-scroll">
            <table className="platform-table test-cases-table">
              <thead>
                <tr>
                  <th>Test Suites</th>
                  <th>Prompt</th>
                  <th>Model</th>
                  <th>Tests</th>
                  <th>Project coverage</th>
                  <th>Target coverage</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {items.map((run) => (
                  <tr
                    key={run.id}
                    className="registry-row"
                    tabIndex={0}
                    onClick={() => navigate(`/test-cases/${run.id}`)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        navigate(`/test-cases/${run.id}`);
                      }
                    }}
                  >
                    <td className="test-suite-name-cell">
                      <strong title={run.name}>{run.name}</strong>
                    </td>
                    <td>{run.promptRole === "baseline" ? "Baseline" : "Final"}</td>
                    <td className="test-suite-model-cell">
                      <code title={run.model}>{run.model}</code>
                    </td>
                    <td>
                      <strong>{run.metrics.testCount}</strong>
                      <small>
                        {run.metrics.testFileCount} files · {run.metrics.targetCount} targets
                      </small>
                      <small>
                        {run.metrics.passed ?? "—"} passed · {run.metrics.failed ?? "—"} failed
                      </small>
                    </td>
                    <td>
                      <CoverageCell
                        value={coverageScore(
                          run.metrics.projectStatementCoverage,
                          run.metrics.projectBranchCoverage,
                        )}
                        tone="project"
                      />
                      <strong>{percentage(run.metrics.projectStatementCoverage)}</strong>
                      <small>Branch {percentage(run.metrics.projectBranchCoverage)}</small>
                    </td>
                    <td>
                      <CoverageCell value={run.metrics.targetScore} tone="target" />
                      <strong>{percentage(run.metrics.targetStatementCoverage)}</strong>
                      <small>Branch {percentage(run.metrics.targetBranchCoverage)}</small>
                    </td>
                    <td>
                      <StatusBadge tone={statusTone(run.status)}>
                        {formatStatus(run.status)}
                      </StatusBadge>
                    </td>
                    <td className="test-suite-created-cell">
                      <time dateTime={run.createdAt}>{timestamp(run.createdAt)}</time>
                    </td>
                    <td>
                      {!readOnly && (
                        <button
                          className="table-action danger-action"
                          onClick={(event) => {
                            event.stopPropagation();
                            deleteMutation.reset();
                            setDeleteTarget(run);
                          }}
                        >
                          Delete
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      {!readOnly && deleteTarget && (
        <div
          className="modal-backdrop"
          role="presentation"
          onMouseDown={() => setDeleteTarget(null)}
        >
          <section
            className="delete-experiment-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-suite-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <span className="delete-dialog-icon">!</span>
            <h2 id="delete-suite-title">Delete test suite?</h2>
            <p>
              <strong>{deleteTarget.name}</strong> and its saved run metadata will be permanently
              removed.
            </p>
            {deleteMutation.isError && (
              <div className="inline-validation-error" role="alert">
                {deleteMutation.error instanceof Error
                  ? deleteMutation.error.message
                  : "The test suite could not be deleted."}
              </div>
            )}
            <div className="delete-dialog-actions">
              <button
                className="secondary-button"
                disabled={deleteMutation.isPending}
                onClick={() => setDeleteTarget(null)}
              >
                Cancel
              </button>
              <button
                className="danger-button"
                disabled={deleteMutation.isPending}
                onClick={() => deleteMutation.mutate(deleteTarget.id)}
              >
                {deleteMutation.isPending ? "Deleting…" : "Delete test suite"}
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
