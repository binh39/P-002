import { useMutation, useQuery } from "@tanstack/react-query";
import { useLocation, useParams } from "wouter";

import { useRepositories } from "@/app/providers";
import { PageHeader, StatCard, StatusBadge } from "@/components/PlatformUI";
import {
  comparisonRunIsActive,
  type ComparisonMetrics,
  type ExperimentStatus,
} from "@/domain/experiments";

const statusLabels: Partial<Record<ExperimentStatus, string>> = {
  comparison_queued: "Queued",
  comparing: "Comparing",
  comparison_succeeded: "Comparison complete",
  in_review: "Ready for review",
  failed: "Failed",
  timed_out: "Timed out",
  cancelled: "Cancelled",
};

function statusTone(status: ExperimentStatus) {
  if (status === "in_review") return "success" as const;
  if (status === "comparison_succeeded") return "warning" as const;
  if (status === "failed" || status === "timed_out" || status === "cancelled") {
    return "danger" as const;
  }
  return "info" as const;
}

function decimal(value: number | null, digits = 3) {
  return value === null ? "—" : value.toFixed(digits);
}

function percent(value: number | null) {
  return value === null ? "—" : `${(value * 100).toFixed(1)}%`;
}

function delta(candidate: number | null, baseline: number | null, percentage = false) {
  if (candidate === null || baseline === null) return "—";
  const difference = candidate - baseline;
  const rendered = percentage ? `${(difference * 100).toFixed(1)} pp` : difference.toFixed(3);
  return `${difference >= 0 ? "+" : ""}${rendered}`;
}

function formatTimestamp(value: string | null) {
  return value
    ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "medium" }).format(
        new Date(value),
      )
    : "—";
}

const metricRows: Array<{
  label: string;
  key: keyof Pick<ComparisonMetrics, "score" | "statementCoverage" | "branchCoverage" | "passRate">;
  percentage?: boolean;
}> = [
  { label: "Evaluation score", key: "score" },
  { label: "Statement coverage", key: "statementCoverage", percentage: true },
  { label: "Branch coverage", key: "branchCoverage", percentage: true },
  { label: "Passing samples", key: "passRate", percentage: true },
];

export default function Comparison() {
  const { runId = "" } = useParams<{ runId: string }>();
  const [, navigate] = useLocation();
  const { experiments } = useRepositories();
  const runQuery = useQuery({
    queryKey: ["comparison-runs", runId],
    queryFn: ({ signal }) => experiments.getComparisonRun(runId, signal),
    enabled: runId !== "",
    refetchInterval: (query) =>
      query.state.data && comparisonRunIsActive(query.state.data.status) ? 3_000 : false,
  });
  const experimentQuery = useQuery({
    queryKey: ["experiments", runQuery.data?.experimentId],
    queryFn: ({ signal }) => experiments.get(runQuery.data?.experimentId ?? "", signal),
    enabled: runQuery.data !== undefined,
  });
  const download = useMutation({
    mutationFn: async (artifactName: string) => ({
      artifactName,
      blob: await experiments.downloadComparisonArtifact(runId, artifactName),
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
        Loading comparison run…
      </div>
    );
  }
  if (runQuery.isError) {
    return (
      <div className="page-state page-state-error" role="alert">
        <h2>Comparison run is unavailable</h2>
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
  const active = comparisonRunIsActive(run.status);
  const complete = run.status === "comparison_succeeded" || run.status === "in_review";

  return (
    <div className="platform-page comparison-run-page">
      <button
        className="back-link"
        onClick={() => navigate(`/optimization-runs/${run.optimizationRunId}`)}
      >
        ← Optimization result
      </button>
      <PageHeader
        eyebrow={`Paired comparison · ${run.id.slice(0, 8)}`}
        title={experiment?.name ?? "Final prompt comparison"}
        description="Baseline and candidate evaluated on the same locked test targets and replicate protocol."
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
            <p>
              The runner is applying both prompts to the locked test split. This page refreshes
              automatically.
            </p>
          </div>
        </section>
      )}

      {run.errorMessage && (
        <section className="baseline-error" role="alert">
          <strong>Comparison failed</strong>
          <pre>{run.errorMessage}</pre>
        </section>
      )}

      {complete && (
        <section
          className={`comparison-decision ${run.promotionEligible ? "is-promoted" : "is-blocked"}`}
        >
          <div>
            <strong>
              {run.promotionEligible
                ? "Candidate passed the promotion gates"
                : "Candidate was not promoted"}
            </strong>
            <p>
              {run.decisionReason || "The final evaluation completed without a decision reason."}
            </p>
          </div>
          <StatusBadge tone={run.promotionEligible ? "success" : "warning"}>
            {run.promotionEligible ? "Eligible" : "Not eligible"}
          </StatusBadge>
        </section>
      )}

      <div className="platform-stats-grid baseline-metrics-grid">
        <StatCard
          label="Baseline score"
          value={decimal(run.baselineMetrics.score)}
          detail="Locked test split"
        />
        <StatCard
          label="Candidate score"
          value={decimal(run.candidateMetrics.score)}
          detail="Same targets and replicates"
          tone="violet"
        />
        <StatCard
          label="Absolute gain"
          value={
            run.absoluteGain === null
              ? "—"
              : `${run.absoluteGain >= 0 ? "+" : ""}${run.absoluteGain.toFixed(3)}`
          }
          detail={
            run.relativeGain === null
              ? "Relative gain unavailable"
              : `${run.relativeGain >= 0 ? "+" : ""}${(run.relativeGain * 100).toFixed(1)}% relative`
          }
          tone="green"
        />
        <StatCard
          label="Evaluation samples"
          value={(run.baselineMetrics.sampleCount ?? 0) + (run.candidateMetrics.sampleCount ?? 0)}
          detail={`${run.testTargetIds.length} targets · ${run.replicateCount} replicates · 2 prompts`}
          tone="orange"
        />
      </div>

      <div className="platform-two-column comparison-details-grid">
        <section className="platform-card table-card">
          <div className="card-heading">
            <div>
              <h2>Paired metrics</h2>
              <p>Candidate deltas are calculated against the immutable baseline.</p>
            </div>
          </div>
          <div className="table-scroll">
            <table className="platform-table comparison-metrics-table">
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Baseline</th>
                  <th>Candidate</th>
                  <th>Delta</th>
                </tr>
              </thead>
              <tbody>
                {metricRows.map(({ label, key, percentage }) => (
                  <tr key={key}>
                    <td>
                      <strong>{label}</strong>
                    </td>
                    <td>
                      {percentage
                        ? percent(run.baselineMetrics[key])
                        : decimal(run.baselineMetrics[key])}
                    </td>
                    <td>
                      {percentage
                        ? percent(run.candidateMetrics[key])
                        : decimal(run.candidateMetrics[key])}
                    </td>
                    <td>
                      {delta(run.candidateMetrics[key], run.baselineMetrics[key], percentage)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="platform-card">
          <div className="card-heading">
            <div>
              <h2>Evaluation protocol</h2>
              <p>Identifiers and reliability signals from this run.</p>
            </div>
          </div>
          <dl className="definition-list comparison-definition-list">
            <div>
              <dt>Test targets</dt>
              <dd>{run.testTargetIds.length}</dd>
            </div>
            <div>
              <dt>Replicates per target</dt>
              <dd>{run.replicateCount}</dd>
            </div>
            <div>
              <dt>Candidate timeouts</dt>
              <dd>{run.candidateMetrics.timeoutCount ?? "—"}</dd>
            </div>
            <div>
              <dt>Candidate flaky targets</dt>
              <dd>{run.candidateMetrics.flakyTargets.length}</dd>
            </div>
            <div>
              <dt>Started</dt>
              <dd>{formatTimestamp(run.startedAt)}</dd>
            </div>
            <div>
              <dt>Finished</dt>
              <dd>{formatTimestamp(run.finishedAt)}</dd>
            </div>
            <div>
              <dt>Prompt version</dt>
              <dd>
                <code>{run.promptVersionId ?? "Not created"}</code>
              </dd>
            </div>
          </dl>
        </section>
      </div>

      <div className="platform-two-column comparison-details-grid">
        <section className="platform-card">
          <div className="card-heading">
            <div>
              <h2>Prompt lineage</h2>
              <p>Digests prove which prompt pair was evaluated.</p>
            </div>
          </div>
          <dl className="definition-list comparison-definition-list">
            <div>
              <dt>Baseline digest</dt>
              <dd>
                <code>{run.baselinePromptDigest}</code>
              </dd>
            </div>
            <div>
              <dt>Candidate digest</dt>
              <dd>
                <code>{run.candidatePromptDigest}</code>
              </dd>
            </div>
          </dl>
        </section>
        <section className="platform-card">
          <div className="card-heading">
            <div>
              <h2>Comparison artifacts</h2>
              <p>Authenticated final-validation downloads.</p>
            </div>
            <StatusBadge tone={run.artifacts.length > 0 ? "success" : "neutral"}>
              {run.artifacts.length} files
            </StatusBadge>
          </div>
          {run.artifacts.length === 0 ? (
            <div className="empty-state">The report will appear after comparison completes.</div>
          ) : (
            <div className="artifact-list">
              {run.artifacts.map((artifact) => (
                <div key={artifact}>
                  <span>
                    <strong>{artifact}</strong>
                    <small>Paired evaluation JSON artifact</small>
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
    </div>
  );
}
