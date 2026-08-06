import { useMutation, useQuery, type UseMutationResult } from "@tanstack/react-query";
import { useLocation, useParams } from "wouter";

import { useRepositories } from "@/app/providers";
import { PageHeader, StatCard, StatusBadge } from "@/components/PlatformUI";
import { baselineRunIsActive, type BaselineRun, type ExperimentStatus } from "@/domain/experiments";

const statusLabels: Partial<Record<ExperimentStatus, string>> = {
  baseline_queued: "Queued",
  baseline_running: "Running",
  baseline_succeeded: "Baseline succeeded",
  failed: "Failed",
  timed_out: "Timed out",
  cancelled: "Cancelled",
};

function statusTone(status: ExperimentStatus) {
  if (status === "baseline_succeeded") return "success" as const;
  if (status === "failed" || status === "timed_out" || status === "cancelled") {
    return "danger" as const;
  }
  return "info" as const;
}

function percentage(value: number | null | undefined) {
  return value === null || value === undefined ? "—" : `${(value * 100).toFixed(1)}%`;
}

function formatTimestamp(value: string | null) {
  return value
    ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "medium" }).format(
        new Date(value),
      )
    : "—";
}

export default function OptimizationProgress() {
  const { runId = "" } = useParams<{ runId: string }>();
  const [, navigate] = useLocation();
  const { experiments } = useRepositories();
  const runQuery = useQuery({
    queryKey: ["baseline-runs", runId],
    queryFn: ({ signal }) => experiments.getBaselineRun(runId, signal),
    enabled: runId !== "",
    refetchInterval: (query) =>
      query.state.data && baselineRunIsActive(query.state.data.status) ? 2_500 : false,
  });
  const experimentQuery = useQuery({
    queryKey: ["experiments", runQuery.data?.experimentId],
    queryFn: ({ signal }) => experiments.get(runQuery.data?.experimentId ?? "", signal),
    enabled: runQuery.data !== undefined,
  });
  const download = useMutation({
    mutationFn: async (artifactName: string) => ({
      artifactName,
      blob: await experiments.downloadBaselineArtifact(runId, artifactName),
    }),
    onSuccess: ({ artifactName, blob }) => {
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = artifactName;
      anchor.click();
      URL.revokeObjectURL(url);
    },
  });
  const startOptimization = useMutation({
    mutationFn: () => experiments.requestOptimization(runQuery.data?.experimentId ?? ""),
    onSuccess: (optimizationRun) => navigate(`/optimization-runs/${optimizationRun.id}`),
  });

  if (runQuery.isPending) {
    return (
      <div className="page-state" role="status">
        Loading baseline run…
      </div>
    );
  }
  if (runQuery.isError) {
    return (
      <div className="page-state page-state-error" role="alert">
        <h2>Baseline run is unavailable</h2>
        <p>
          {runQuery.error instanceof Error
            ? runQuery.error.message
            : "An unexpected error occurred."}
        </p>
        <button onClick={() => runQuery.refetch()}>Try again</button>
      </div>
    );
  }

  const run = runQuery.data;
  const active = baselineRunIsActive(run.status);
  const experiment = experimentQuery.data;
  const canStartOptimization =
    run.status === "baseline_succeeded" &&
    experiment?.status === "baseline_succeeded" &&
    experiment.optimizationEligible;
  const canOpenOptimization =
    experiment?.optimizationRunId && experiment.status !== "baseline_succeeded";

  return (
    <div className="platform-page baseline-run-page">
      <button className="back-link" onClick={() => navigate("/experiments/new")}>
        ← New experiment
      </button>
      <PageHeader
        eyebrow={`Baseline run · ${run.id.slice(0, 8)}`}
        title={experiment?.name ?? "Baseline evaluation"}
        description="Real-time coverage result from the isolated production runner."
        actions={
          <>
            <StatusBadge tone={statusTone(run.status)}>
              {statusLabels[run.status] ?? run.status.replace(/_/g, " ")}
            </StatusBadge>
            {canOpenOptimization && (
              <button
                className="primary-button"
                onClick={() => navigate(`/optimization-runs/${experiment.optimizationRunId}`)}
              >
                Open optimization
              </button>
            )}
            {canStartOptimization && (
              <button
                className="primary-button"
                disabled={startOptimization.isPending}
                onClick={() => startOptimization.mutate()}
              >
                {experiment.optimizationRunId ? "Retry optimization" : "Start optimization"}
              </button>
            )}
          </>
        }
      />

      {run.status === "baseline_succeeded" && experiment && !experiment.optimizationEligible && (
        <section className="platform-callout">
          <div>
            <strong>More targets are required for optimization</strong>
            <p>
              Create an experiment with at least three functions so train, validation and test
              splits are non-empty.
            </p>
          </div>
          <button className="secondary-button" onClick={() => navigate("/experiments/new")}>
            Create another experiment
          </button>
        </section>
      )}

      {startOptimization.isError && (
        <div className="auth-error" role="alert">
          {startOptimization.error instanceof Error
            ? startOptimization.error.message
            : "Optimization could not be started."}
        </div>
      )}

      {active && (
        <section className="baseline-running-card" role="status">
          <span className="baseline-spinner" aria-hidden="true" />
          <div>
            <h2>
              {run.status === "baseline_queued" ? "Waiting for a runner" : "Baseline is running"}
            </h2>
            <p>The page refreshes automatically. You can leave and return with this run URL.</p>
          </div>
        </section>
      )}

      {run.errorMessage && (
        <section className="baseline-error" role="alert">
          <strong>Baseline execution failed</strong>
          <pre>{run.errorMessage}</pre>
        </section>
      )}

      <div className="platform-stats-grid baseline-metrics-grid">
        <StatCard
          label="Coverage score"
          value={percentage(run.coverageScore)}
          detail="Aggregate target score"
        />
        <StatCard
          label="Statement coverage"
          value={percentage(run.statementCoverage)}
          detail="Executed statements"
          tone="violet"
        />
        <StatCard
          label="Branch coverage"
          value={percentage(run.branchCoverage)}
          detail="Executed branch outcomes"
          tone="green"
        />
        <StatCard
          label="Targets"
          value={run.targetCount}
          detail={`${Object.keys(run.targetMetrics).length} reported`}
          tone="orange"
        />
      </div>

      <div className="platform-two-column baseline-details-grid">
        <section className="platform-card">
          <div className="card-heading">
            <div>
              <h2>Run details</h2>
              <p>Immutable identifiers and execution timestamps.</p>
            </div>
          </div>
          <dl className="definition-list">
            <div>
              <dt>Run ID</dt>
              <dd>
                <code>{run.id}</code>
              </dd>
            </div>
            <div>
              <dt>Experiment ID</dt>
              <dd>
                <code>{run.experimentId}</code>
              </dd>
            </div>
            <div>
              <dt>Prompt digest</dt>
              <dd>
                <code>{run.promptDigest ?? "Pending"}</code>
              </dd>
            </div>
            <div>
              <dt>Created</dt>
              <dd>{formatTimestamp(run.createdAt)}</dd>
            </div>
            <div>
              <dt>Started</dt>
              <dd>{formatTimestamp(run.startedAt)}</dd>
            </div>
            <div>
              <dt>Finished</dt>
              <dd>{formatTimestamp(run.finishedAt)}</dd>
            </div>
          </dl>
        </section>

        <ArtifactsPanel run={run} download={download} />
      </div>

      <section className="platform-card table-card baseline-targets-card">
        <div className="table-toolbar">
          <div>
            <h2>Target metrics</h2>
            <p>Coverage reported for every selected qualified function.</p>
          </div>
        </div>
        {Object.keys(run.targetMetrics).length === 0 ? (
          <div className="empty-state">
            {active
              ? "Metrics will appear when the runner finishes."
              : "No target metrics were published."}
          </div>
        ) : (
          <div className="table-scroll">
            <table className="platform-table">
              <thead>
                <tr>
                  <th>Target</th>
                  <th>Score</th>
                  <th>Statements</th>
                  <th>Statement coverage</th>
                  <th>Branches</th>
                  <th>Branch coverage</th>
                  <th>Valid</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(run.targetMetrics).map(([target, metric]) => (
                  <tr key={target}>
                    <td>
                      <code>{target}</code>
                    </td>
                    <td>{percentage(metric.score)}</td>
                    <td>
                      {metric.coveredStatements ?? 0} / {metric.numStatements ?? 0}
                    </td>
                    <td>{percentage(metric.statementCoverage)}</td>
                    <td>
                      {metric.coveredBranches ?? 0} / {metric.numBranches ?? 0}
                    </td>
                    <td>{percentage(metric.branchCoverage)}</td>
                    <td>
                      <StatusBadge tone={metric.valid === false ? "danger" : "success"}>
                        {metric.valid === false ? "Invalid" : "Valid"}
                      </StatusBadge>
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

function ArtifactsPanel({
  run,
  download,
}: {
  run: BaselineRun;
  download: UseMutationResult<{ artifactName: string; blob: Blob }, Error, string>;
}) {
  return (
    <section className="platform-card baseline-artifacts-card">
      <div className="card-heading">
        <div>
          <h2>Artifacts</h2>
          <p>Authenticated downloads produced by this baseline.</p>
        </div>
        <StatusBadge tone={run.artifacts.length > 0 ? "success" : "neutral"}>
          {run.artifacts.length} files
        </StatusBadge>
      </div>
      {run.artifacts.length === 0 ? (
        <div className="empty-state">Artifacts will appear after a successful baseline.</div>
      ) : (
        <div className="artifact-list">
          {run.artifacts.map((artifact) => (
            <div key={artifact}>
              <span>
                <strong>{artifact}</strong>
                <small>{artifactKind(artifact)}</small>
              </span>
              <button
                className="table-action"
                disabled={download.isPending}
                onClick={() => download.mutate(artifact)}
              >
                Download
              </button>
            </div>
          ))}
        </div>
      )}
      {download.isError && (
        <div className="auth-error" role="alert">
          {download.error.message}
        </div>
      )}
    </section>
  );
}

function artifactKind(name: string) {
  if (name.endsWith(".zip")) return "Generated test archive";
  if (name.endsWith(".json")) return "JSON report";
  if (name.endsWith(".jsonl")) return "Execution trace";
  if (name.endsWith(".log")) return "Runner log";
  return "Coverage artifact";
}
