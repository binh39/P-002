import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useLocation } from "wouter";

import { useRepositories } from "@/app/providers";
import { PageHeader, StatCard, StatusBadge } from "@/components/PlatformUI";
import type { ExperimentStatus } from "@/domain/experiments";

function statusTone(status: ExperimentStatus) {
  if (
    status === "baseline_succeeded" ||
    status === "optimization_succeeded" ||
    status === "approved"
  ) {
    return "success" as const;
  }
  if (status === "failed" || status === "timed_out" || status === "rejected")
    return "danger" as const;
  if (status === "draft" || status === "cancelled") return "neutral" as const;
  return "info" as const;
}

function formatStatus(status: ExperimentStatus) {
  return status.replace(/_/g, " ").replace(/^./, (letter) => letter.toUpperCase());
}

export default function Experiments() {
  const [, navigate] = useLocation();
  const { experiments } = useRepositories();
  const queryClient = useQueryClient();
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);
  const query = useQuery({
    queryKey: ["experiments"],
    queryFn: ({ signal }) => experiments.list(signal),
    refetchInterval: (current) =>
      current.state.data?.some((item) =>
        [
          "baseline_queued",
          "baseline_running",
          "optimization_queued",
          "optimizing",
          "candidate_evaluating",
          "comparison_queued",
          "comparing",
        ].includes(item.status),
      )
        ? 3_000
        : false,
  });
  const deleteExperiment = useMutation({
    mutationFn: (experimentId: string) => experiments.delete(experimentId),
    onSuccess: async () => {
      setDeleteTarget(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["experiments"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
      ]);
    },
  });

  if (query.isPending)
    return (
      <div className="page-state" role="status">
        Loading experiments…
      </div>
    );
  if (query.isError) {
    return (
      <div className="page-state page-state-error" role="alert">
        <h2>Experiments are unavailable</h2>
        <p>
          {query.error instanceof Error ? query.error.message : "An unexpected error occurred."}
        </p>
        <button onClick={() => query.refetch()}>Try again</button>
      </div>
    );
  }

  const items = query.data;
  const active = items.filter((item) =>
    [
      "baseline_queued",
      "baseline_running",
      "optimization_queued",
      "optimizing",
      "candidate_evaluating",
      "comparison_queued",
      "comparing",
    ].includes(item.status),
  ).length;
  const completed = items.filter((item) => item.status === "baseline_succeeded").length;
  const failed = items.filter((item) => item.status === "failed").length;

  return (
    <div className="platform-page experiments-page">
      <PageHeader
        title="Experiments"
        actions={
          <button className="primary-button" onClick={() => navigate("/experiments/new")}>
            + Create experiment
          </button>
        }
      />
      <div className="platform-stats-grid">
        <StatCard label="Total experiments" value={items.length} />
        <StatCard label="Active" value={active} tone="violet" />
        <StatCard label="Baselines complete" value={completed} tone="green" />
        <StatCard label="Failed" value={failed} tone="orange" />
      </div>
      <section className="platform-card table-card">
        <div className="table-toolbar">
          <div>
            <h2>All experiments</h2>
          </div>
        </div>
        {items.length === 0 ? (
          <div className="empty-state">
            No experiments yet. Create one from an analyzed Python project.
          </div>
        ) : (
          <div className="table-scroll">
            <table className="platform-table">
              <thead>
                <tr>
                  <th>Experiment</th>
                  <th>Targets</th>
                  <th>Dataset split</th>
                  <th>Status</th>
                  <th>Optimization</th>
                  <th>Updated</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr
                    key={item.id}
                    className={item.optimizationRunId ? "registry-row" : undefined}
                    tabIndex={item.optimizationRunId ? 0 : undefined}
                    onClick={() => {
                      if (item.optimizationRunId) {
                        navigate(`/optimization-runs/${item.optimizationRunId}`);
                      }
                    }}
                    onKeyDown={(event) => {
                      if (
                        item.optimizationRunId &&
                        (event.key === "Enter" || event.key === " ")
                      ) {
                        event.preventDefault();
                        navigate(`/optimization-runs/${item.optimizationRunId}`);
                      }
                    }}
                  >
                    <td>
                      <strong>{item.name}</strong>
                      <small>{item.creatorName ?? "Unknown user"}</small>
                    </td>
                    <td>{item.targetFunctionIds.length}</td>
                    <td>
                      {Object.entries(item.datasetSplits)
                        .map(([name, ids]) => `${name}: ${ids.length}`)
                        .join(" · ")}
                    </td>
                    <td>
                      <StatusBadge tone={statusTone(item.status)}>
                        {formatStatus(item.status)}
                      </StatusBadge>
                    </td>
                    <td>{item.optimizationEligible ? "Eligible" : "Needs at least 3 targets"}</td>
                    <td>
                      {new Intl.DateTimeFormat(undefined, {
                        dateStyle: "medium",
                        timeStyle: "short",
                      }).format(new Date(item.updatedAt))}
                    </td>
                    <td>
                      <div className="experiment-row-actions">
                        <button
                          className="table-action danger-action"
                          onClick={() => {
                            deleteExperiment.reset();
                            setDeleteTarget({ id: item.id, name: item.name });
                          }}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      {deleteTarget && (
        <div
          className="modal-backdrop"
          role="presentation"
          onMouseDown={() => setDeleteTarget(null)}
        >
          <section
            className="delete-experiment-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-experiment-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <span className="delete-dialog-icon">!</span>
            <h2 id="delete-experiment-title">Delete experiment?</h2>
            <p>
              <strong>{deleteTarget.name}</strong> and its run references will be permanently
              removed. Cloud artifacts are retained according to the backend retention policy.
            </p>
            {deleteExperiment.isError && (
              <div className="inline-validation-error" role="alert">
                {deleteExperiment.error instanceof Error
                  ? deleteExperiment.error.message
                  : "The experiment could not be deleted."}
              </div>
            )}
            <div className="delete-dialog-actions">
              <button
                className="secondary-button"
                disabled={deleteExperiment.isPending}
                onClick={() => setDeleteTarget(null)}
              >
                Cancel
              </button>
              <button
                className="danger-button"
                disabled={deleteExperiment.isPending}
                onClick={() => deleteExperiment.mutate(deleteTarget.id)}
              >
                {deleteExperiment.isPending ? "Deleting…" : "Delete experiment"}
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
