import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useLocation } from "wouter";

import { useRepositories } from "@/app/providers";
import { IC } from "@/components/Icons";
import { PageHeader, StatusBadge } from "@/components/PlatformUI";
import type {
  ExperimentStatus,
  PromptCoverageMetrics,
  PromptRegistryEntry,
} from "@/domain/experiments";

function percentage(value: number | null) {
  return value === null ? "—" : `${(value * 100).toFixed(1)}%`;
}

function coverageSummary(metrics: PromptCoverageMetrics) {
  return `${percentage(metrics.statementCoverage)} stmt · ${percentage(metrics.branchCoverage)} branch`;
}

function scoreWidth(value: number | null) {
  return `${Math.round(Math.max(0, Math.min(1, value ?? 0)) * 100)}%`;
}

function ScoreCell({
  metrics,
  tone,
}: {
  metrics: PromptCoverageMetrics;
  tone: "baseline" | "final";
}) {
  if (metrics.score === null) return <span className="muted-cell">Pending optimization</span>;
  return (
    <div
      className="registry-score"
      title={`Score ${percentage(metrics.score)} · ${coverageSummary(metrics)}`}
    >
      <strong>{percentage(metrics.score)}</strong>
      <span className={`registry-score-bar is-${tone}`} aria-hidden="true">
        <span style={{ width: scoreWidth(metrics.score) }} />
      </span>
    </div>
  );
}

function formatTimestamp(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(
    new Date(value),
  );
}

function formatCost(value: number | null | undefined) {
  return value == null ? "—" : value.toFixed(2);
}

function statusTone(status: ExperimentStatus) {
  if (status === "failed" || status === "timed_out" || status === "rejected")
    return "danger" as const;
  if (status === "draft" || status === "cancelled") return "neutral" as const;
  return "info" as const;
}

function formatStatus(status: ExperimentStatus) {
  return status.replace(/_/g, " ").replace(/^./, (character) => character.toUpperCase());
}

function isSettled(entry: PromptRegistryEntry) {
  return entry.optimized !== null || ["approved", "rejected"].includes(entry.status);
}

export default function Registry() {
  const [, navigate] = useLocation();
  const { promptRegistry } = useRepositories();
  const [search, setSearch] = useState("");
  const [modelFilter, setModelFilter] = useState("all");
  const query = useQuery({
    queryKey: ["prompt-registry"],
    queryFn: ({ signal }) => promptRegistry.list(signal),
  });

  if (query.isPending) {
    return (
      <div className="page-state" role="status">
        Loading prompt registry…
      </div>
    );
  }
  if (query.isError) {
    return (
      <div className="page-state page-state-error" role="alert">
        <h2>Prompt Registry is unavailable</h2>
        <p>
          {query.error instanceof Error ? query.error.message : "An unexpected error occurred."}
        </p>
        <button onClick={() => query.refetch()}>Try again</button>
      </div>
    );
  }

  const models = [...new Set(query.data.items.map((entry) => entry.baseline.coverupModel))].sort();
  const normalizedSearch = search.trim().toLowerCase();
  const entries = query.data.items.filter((entry) => {
    const matchesSearch =
      !normalizedSearch ||
      [entry.experimentId, entry.experimentName, ...entry.projectNames]
        .join(" ")
        .toLowerCase()
        .includes(normalizedSearch);
    return matchesSearch && (modelFilter === "all" || entry.baseline.coverupModel === modelFilter);
  });

  return (
    <div className="platform-page registry-page">
      <PageHeader title="Prompt Registry" />

      <section className="platform-card registry-filters">
        <label className="registry-search-field">
          <IC.Search />
          <input
            aria-label="Search experiments"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search experiment, project, or ID…"
          />
        </label>
        <label className="registry-model-filter">
          <span className="sr-only">Generation model</span>
          <select
            aria-label="Generation model"
            value={modelFilter}
            onChange={(event) => setModelFilter(event.target.value)}
          >
            <option value="all">All models</option>
            {models.map((model) => (
              <option key={model} value={model}>
                {model}
              </option>
            ))}
          </select>
        </label>
        <span className="registry-result-count">{entries.length} results</span>
      </section>

      <section className="platform-card table-card">
        {entries.length === 0 ? (
          <div className="empty-state">
            {query.data.total === 0
              ? "No experiments yet. Create and run an experiment to register its prompt snapshots."
              : "No registry entries match the selected filters."}
          </div>
        ) : (
          <div className="table-scroll">
            <table className="platform-table registry-table">
              <thead>
                <tr>
                  <th>Experiment</th>
                  <th>Project</th>
                  <th>Baseline</th>
                  <th>Final prompt</th>
                  <th>Delta</th>
                  <th>Cost</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => {
                  const inactive = isSettled(entry);
                  return (
                    <tr
                      key={entry.experimentId}
                      className="registry-row"
                      tabIndex={0}
                      onClick={() => navigate(`/prompts/${entry.experimentId}`)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          navigate(`/prompts/${entry.experimentId}`);
                        }
                      }}
                    >
                      <td className="registry-experiment-cell">
                        <strong title={entry.experimentName}>{entry.experimentName}</strong>
                        <small title={entry.experimentId}>{entry.experimentId}</small>
                        {!inactive && (
                          <StatusBadge tone={statusTone(entry.status)}>
                            {formatStatus(entry.status)}
                          </StatusBadge>
                        )}
                      </td>
                      <td
                        className="registry-project-cell"
                        title={entry.projectNames.join(", ") || entry.projectIds.join(", ")}
                      >
                        {entry.projectNames.join(", ") || entry.projectIds.join(", ")}
                      </td>
                      <td>
                        <ScoreCell metrics={entry.baselineMetrics} tone="baseline" />
                      </td>
                      <td>
                        <ScoreCell metrics={entry.optimizedMetrics} tone="final" />
                      </td>
                      <td>
                        {entry.absoluteGain === null ? (
                          <span className="muted-cell">—</span>
                        ) : (
                          <strong
                            className={
                              entry.absoluteGain >= 0 ? "metric-positive" : "metric-negative"
                            }
                          >
                            {entry.absoluteGain >= 0 ? "+" : ""}
                            {(entry.absoluteGain * 100).toFixed(1)}%
                          </strong>
                        )}
                      </td>
                      <td>
                        {formatCost(
                          entry.optimized?.estimatedCostUsd ?? entry.baseline.estimatedCostUsd,
                        ) ?? "—"}
                      </td>
                      <td>{formatTimestamp(entry.updatedAt)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
