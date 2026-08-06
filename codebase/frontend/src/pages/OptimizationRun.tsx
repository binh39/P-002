import { useMutation, useQuery } from "@tanstack/react-query";
import { useLocation, useParams } from "wouter";

import { useRepositories } from "@/app/providers";
import { PageHeader, StatCard, StatusBadge } from "@/components/PlatformUI";
import { optimizationRunIsActive, type ExperimentStatus } from "@/domain/experiments";

const statusLabels: Partial<Record<ExperimentStatus, string>> = {
  optimization_queued: "Queued",
  optimizing: "Optimizing",
  candidate_evaluating: "Evaluating candidate",
  optimization_succeeded: "Optimization succeeded",
  failed: "Failed",
  timed_out: "Timed out",
  cancelled: "Cancelled",
};

function statusTone(status: ExperimentStatus) {
  if (status === "optimization_succeeded") return "success" as const;
  if (status === "failed" || status === "timed_out" || status === "cancelled") {
    return "danger" as const;
  }
  return "info" as const;
}

function score(value: number | null) {
  return value === null ? "—" : value.toFixed(3);
}

function formatTimestamp(value: string | null) {
  return value
    ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "medium" }).format(
        new Date(value),
      )
    : "—";
}

export default function OptimizationRun() {
  const { runId = "" } = useParams<{ runId: string }>();
  const [, navigate] = useLocation();
  const { experiments } = useRepositories();
  const runQuery = useQuery({
    queryKey: ["optimization-runs", runId],
    queryFn: ({ signal }) => experiments.getOptimizationRun(runId, signal),
    enabled: runId !== "",
    refetchInterval: (query) =>
      query.state.data && optimizationRunIsActive(query.state.data.status) ? 3_000 : false,
  });
  const experimentQuery = useQuery({
    queryKey: ["experiments", runQuery.data?.experimentId],
    queryFn: ({ signal }) => experiments.get(runQuery.data?.experimentId ?? "", signal),
    enabled: runQuery.data !== undefined,
  });
  const download = useMutation({
    mutationFn: async (artifactName: string) => ({
      artifactName,
      blob: await experiments.downloadOptimizationArtifact(runId, artifactName),
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

  if (runQuery.isPending) {
    return (
      <div className="page-state" role="status">
        Loading optimization run…
      </div>
    );
  }
  if (runQuery.isError) {
    return (
      <div className="page-state page-state-error" role="alert">
        <h2>Optimization run is unavailable</h2>
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
  const experiment = experimentQuery.data;
  const active = optimizationRunIsActive(run.status);
  const gain =
    run.baselineValidationScore !== null && run.candidateValidationScore !== null
      ? run.candidateValidationScore - run.baselineValidationScore
      : null;

  return (
    <div className="platform-page optimization-run-page">
      <button
        className="back-link"
        onClick={() =>
          experiment?.baselineRunId
            ? navigate(`/runs/${experiment.baselineRunId}`)
            : navigate("/experiments")
        }
      >
        ← Baseline result
      </button>
      <PageHeader
        eyebrow={`Optimization run · ${run.id.slice(0, 8)}`}
        title={experiment?.name ?? "Prompt optimization"}
        description="GEPA candidate search and validation results from the production pipeline."
        actions={
          <StatusBadge tone={statusTone(run.status)}>
            {statusLabels[run.status] ?? run.status.replace(/_/g, " ")}
          </StatusBadge>
        }
      />

      {active && (
        <section className="baseline-running-card" role="status">
          <span className="baseline-spinner" aria-hidden="true" />
          <div>
            <h2>{statusLabels[run.status]}</h2>
            <p>The optimizer is evaluating prompt candidates. This page refreshes automatically.</p>
          </div>
        </section>
      )}

      {run.errorMessage && (
        <section className="baseline-error" role="alert">
          <strong>Optimization failed</strong>
          <pre>{run.errorMessage}</pre>
        </section>
      )}

      {run.status === "optimization_succeeded" && (
        <section className="optimization-ready-callout">
          <div>
            <strong>Candidate prompt is locked</strong>
            <p>The candidate is ready for an isolated paired comparison against the baseline.</p>
          </div>
          <StatusBadge tone="success">Ready for comparison</StatusBadge>
        </section>
      )}

      <div className="platform-stats-grid baseline-metrics-grid">
        <StatCard
          label="Baseline validation"
          value={score(run.baselineValidationScore)}
          detail="Parent prompt score"
        />
        <StatCard
          label="Candidate validation"
          value={score(run.candidateValidationScore)}
          detail="Best candidate score"
          tone="violet"
        />
        <StatCard
          label="Absolute gain"
          value={gain === null ? "—" : `${gain >= 0 ? "+" : ""}${gain.toFixed(3)}`}
          detail="Candidate minus baseline"
          tone="green"
        />
        <StatCard
          label="Candidates"
          value={run.candidateCount}
          detail={`${run.metricCalls} metric calls`}
          tone="orange"
        />
      </div>

      <div className="platform-two-column optimization-details-grid">
        <section className="platform-card">
          <div className="card-heading">
            <div>
              <h2>Prompt lineage</h2>
              <p>Digests identify the immutable parent and selected candidate.</p>
            </div>
          </div>
          <dl className="definition-list">
            <div>
              <dt>Parent digest</dt>
              <dd>
                <code>{run.parentPromptDigest}</code>
              </dd>
            </div>
            <div>
              <dt>Candidate digest</dt>
              <dd>
                <code>{run.candidatePromptDigest ?? "Pending"}</code>
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

        <section className="platform-card">
          <div className="card-heading">
            <div>
              <h2>Optimization artifacts</h2>
              <p>Authenticated candidate and GEPA result downloads.</p>
            </div>
            <StatusBadge tone={run.artifacts.length > 0 ? "success" : "neutral"}>
              {run.artifacts.length} files
            </StatusBadge>
          </div>
          {run.artifacts.length === 0 ? (
            <div className="empty-state">Artifacts will appear after optimization succeeds.</div>
          ) : (
            <div className="artifact-list">
              {run.artifacts.map((artifact) => (
                <div key={artifact}>
                  <span>
                    <strong>{artifact}</strong>
                    <small>Optimization JSON artifact</small>
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
      </div>

      <section className="platform-card candidate-prompt-card">
        <div className="card-heading">
          <div>
            <h2>Selected candidate prompt</h2>
            <p>The exact prompt returned by the optimizer, without UI fixture content.</p>
          </div>
        </div>
        {!run.candidatePrompt ? (
          <div className="empty-state">
            {active
              ? "The best candidate will appear when optimization finishes."
              : "No candidate prompt was published."}
          </div>
        ) : (
          <div className="candidate-prompt-sections">
            {Object.entries(run.candidatePrompt).map(([name, content]) => (
              <section key={name}>
                <h3>{name.replace(/_/g, " ")}</h3>
                <pre>{content}</pre>
              </section>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
