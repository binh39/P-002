import { useQuery } from "@tanstack/react-query";
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
        ].includes(item.status),
      )
        ? 3_000
        : false,
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
    ].includes(item.status),
  ).length;
  const completed = items.filter((item) => item.status === "baseline_succeeded").length;
  const failed = items.filter((item) => item.status === "failed").length;

  return (
    <div className="platform-page">
      <PageHeader
        eyebrow="Evaluation workspace"
        title="Experiments"
        description="Create and monitor real prompt evaluation runs."
        actions={
          <button className="primary-button" onClick={() => navigate("/experiments/new")}>
            + Create experiment
          </button>
        }
      />
      <div className="platform-stats-grid">
        <StatCard label="Total experiments" value={items.length} detail="Owned by your account" />
        <StatCard label="Active" value={active} detail="Queued or running" tone="violet" />
        <StatCard
          label="Baselines complete"
          value={completed}
          detail="Ready for optimization"
          tone="green"
        />
        <StatCard label="Failed" value={failed} detail="Review the run error" tone="orange" />
      </div>
      <section className="platform-card table-card">
        <div className="table-toolbar">
          <div>
            <h2>All experiments</h2>
            <p>Live records from the PromptOpt API.</p>
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
                  <tr key={item.id}>
                    <td>
                      <strong>{item.name}</strong>
                      <small>{item.id}</small>
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
                      {item.optimizationRunId &&
                      [
                        "optimization_queued",
                        "optimizing",
                        "candidate_evaluating",
                        "optimization_succeeded",
                      ].includes(item.status) ? (
                        <button
                          className="table-action"
                          onClick={() => navigate(`/optimization-runs/${item.optimizationRunId}`)}
                        >
                          Open optimization
                        </button>
                      ) : item.baselineRunId ? (
                        <button
                          className="table-action"
                          onClick={() => navigate(`/runs/${item.baselineRunId}`)}
                        >
                          Open baseline
                        </button>
                      ) : (
                        <span className="muted-cell">Draft</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
