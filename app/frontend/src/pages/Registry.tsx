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

function formatTimestamp(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(
    new Date(value),
  );
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
      <PageHeader
        eyebrow="Experiment prompt snapshots"
        title="Prompt Registry"
        description={`${query.data.total} experiment${query.data.total === 1 ? "" : "s"} with immutable baseline and final prompt bundles.`}
      />

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
          <span>Generation model</span>
          <select value={modelFilter} onChange={(event) => setModelFilter(event.target.value)}>
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
                  <th>Models</th>
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
                      <td>
                        <strong>{entry.experimentName}</strong>
                        <small>{entry.experimentId}</small>
                        {!inactive && (
                          <StatusBadge tone={statusTone(entry.status)}>
                            {formatStatus(entry.status)}
                          </StatusBadge>
                        )}
                      </td>
                      <td>{entry.projectNames.join(", ") || entry.projectIds.join(", ")}</td>
                      <td>
                        <strong>{percentage(entry.baselineMetrics.score)}</strong>
                        <small>{coverageSummary(entry.baselineMetrics)}</small>
                      </td>
                      <td>
                        {entry.optimized ? (
                          <>
                            <strong>{percentage(entry.optimizedMetrics.score)}</strong>
                            <small>{coverageSummary(entry.optimizedMetrics)}</small>
                          </>
                        ) : (
                          <span className="muted-cell">Pending optimization</span>
                        )}
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
                            {(entry.absoluteGain * 100).toFixed(1)} pp
                          </strong>
                        )}
                      </td>
                      <td>
                        <code>{entry.baseline.coverupModel}</code>
                        <small>Optimize: {entry.baseline.optimizeModel}</small>
                      </td>
                      <td>
                        {entry.optimized?.estimatedCostUsd ??
                          entry.baseline.estimatedCostUsd ??
                          "—"}
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
