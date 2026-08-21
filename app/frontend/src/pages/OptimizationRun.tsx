import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useLocation, useParams } from "wouter";

import { useRepositories } from "@/app/providers";
import { PageHeader, StatCard, StatusBadge } from "@/components/PlatformUI";
import {
  optimizationRunIsActive,
  type EvolutionIteration,
  type ExperimentStatus,
  type OptimizationEvolution,
  type PromptBundle,
} from "@/domain/experiments";

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

function PromptCard({
  title,
  description,
  prompt,
  emptyMessage,
}: {
  title: string;
  description: string;
  prompt: PromptBundle | null;
  emptyMessage: string;
}) {
  return (
    <section className="platform-card candidate-prompt-card">
      <div className="card-heading">
        <div>
          <h2>{title}</h2>
          <p>{description}</p>
        </div>
      </div>
      {!prompt ? (
        <div className="empty-state">{emptyMessage}</div>
      ) : (
        <div className="candidate-prompt-sections">
          {Object.entries(prompt).map(([name, content]) => (
            <section key={name}>
              <h3>{name.replace(/_/g, " ")}</h3>
              <pre>{content}</pre>
            </section>
          ))}
        </div>
      )}
    </section>
  );
}

function metric(value: number | null) {
  return value === null ? "—" : value.toFixed(4);
}

function decisionTone(decision: string) {
  if (decision === "Accepted" || decision === "Baseline evaluated") return "success" as const;
  if (decision === "Rejected" || decision.includes("failed")) return "danger" as const;
  return "info" as const;
}

function FlowValue({ children }: { children: React.ReactNode }) {
  return <strong>{children ?? "—"}</strong>;
}

function IterationFlow({ iteration }: { iteration: EvolutionIteration }) {
  return (
    <div className="evolution-flow" data-testid="evolution-flow">
      <div className="evolution-flow-title">
        <div>
          <span>Selected evolution step</span>
          <h3>Iteration {iteration.iteration}</h3>
        </div>
        <StatusBadge tone={decisionTone(iteration.decision)}>{iteration.decision}</StatusBadge>
      </div>
      <dl className="evolution-flow-tree">
        <div>
          <dt>Strategy</dt>
          <dd>
            <FlowValue>{iteration.strategy}</FlowValue>
          </dd>
        </div>
        <div>
          <dt>Parent</dt>
          <dd>
            <FlowValue>{iteration.parentProgram}</FlowValue>
          </dd>
        </div>
        <div>
          <dt>Parent validation score</dt>
          <dd>
            <FlowValue>{metric(iteration.parentValidationScore)}</FlowValue>
          </dd>
        </div>
        <div>
          <dt>Component</dt>
          <dd>
            <FlowValue>{iteration.component}</FlowValue>
          </dd>
        </div>
        <div className="evolution-flow-prompt">
          <dt>Proposed prompt</dt>
          <dd>
            {iteration.proposedPrompt ? (
              <pre>{iteration.proposedPrompt}</pre>
            ) : (
              <FlowValue>—</FlowValue>
            )}
          </dd>
        </div>
        <div>
          <dt>Parent minibatch sum</dt>
          <dd>
            <FlowValue>{metric(iteration.parentMinibatchSum)}</FlowValue>
          </dd>
        </div>
        <div>
          <dt>Candidate minibatch sum</dt>
          <dd>
            <FlowValue>{metric(iteration.candidateMinibatchSum)}</FlowValue>
          </dd>
        </div>
        <div>
          <dt>Decision</dt>
          <dd>
            <FlowValue>{iteration.decision}</FlowValue>
            {iteration.outcomeDetail ? <small>{iteration.outcomeDetail}</small> : null}
          </dd>
        </div>
        <div>
          <dt>Best validation candidate</dt>
          <dd>
            <FlowValue>{iteration.bestCandidateChanged ? "Updated" : "Unchanged"}</FlowValue>
            <small>
              Statement {metric(iteration.bestStatement)} · Branch {metric(iteration.bestBranch)} ·
              Score {metric(iteration.bestScore)}
            </small>
          </dd>
        </div>
      </dl>
    </div>
  );
}

function EvolutionPanel({ evolution }: { evolution: OptimizationEvolution }) {
  const [selectedIteration, setSelectedIteration] = useState<number | null>(null);
  const selected =
    evolution.iterations.find((item) => item.iteration === selectedIteration) ??
    evolution.iterations.at(-1) ??
    null;

  return (
    <section className="platform-card evolution-card">
      <div className="card-heading evolution-heading">
        <div>
          <h2>Live GEPA evolution</h2>
          <p>Iteration history and metrics for the aggregate-best validation candidate.</p>
        </div>
        <StatusBadge tone={evolution.available ? "success" : "neutral"}>
          {evolution.available ? `${evolution.iterations.length} iterations` : "Waiting for logs"}
        </StatusBadge>
      </div>

      {!evolution.available || !selected ? (
        <div className="evolution-empty">
          <span className="baseline-spinner" aria-hidden="true" />
          <div>
            <strong>Evolution data is not available yet</strong>
            <p>{evolution.message}</p>
          </div>
        </div>
      ) : (
        <>
          <div className="evolution-workspace">
            <aside className="evolution-history" aria-label="Iteration history">
              <div className="evolution-panel-label">History</div>
              <div className="evolution-history-list">
                {[...evolution.iterations].reverse().map((iteration) => (
                  <button
                    className={iteration.iteration === selected.iteration ? "is-selected" : ""}
                    key={iteration.iteration}
                    onClick={() => setSelectedIteration(iteration.iteration)}
                  >
                    <span>
                      <strong>Iteration {iteration.iteration}</strong>
                      <small>{iteration.strategy}</small>
                    </span>
                    <span
                      className={`iteration-decision is-${iteration.decision.toLowerCase().replace(/\s+/g, "-")}`}
                    >
                      {iteration.decision}
                    </span>
                  </button>
                ))}
              </div>
            </aside>

            <IterationFlow iteration={selected} />

            <div className="evolution-chart-panel">
              <div className="evolution-panel-label">Best validation metrics</div>
              <p className="evolution-chart-description">
                Statement and branch are micro-averaged over executable units for the same
                aggregate-best candidate as score, not separate Pareto-front maxima.
              </p>
              <div
                className="evolution-chart"
                aria-label="Statement, branch and score by iteration"
              >
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={evolution.metrics}
                    margin={{ top: 18, right: 18, bottom: 8, left: -12 }}
                  >
                    <CartesianGrid strokeDasharray="4 4" stroke="#e4e7ec" />
                    <XAxis dataKey="iteration" tickFormatter={(value) => `I${value}`} />
                    <YAxis
                      domain={[0, "auto"]}
                      tickFormatter={(value) => Number(value).toFixed(2)}
                    />
                    <Tooltip
                      labelFormatter={(value) => `Iteration ${value}`}
                      formatter={(value) => [Number(value).toFixed(4)]}
                    />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="statement"
                      name="Statement"
                      stroke="#7c6cf2"
                      strokeWidth={2.5}
                      connectNulls
                    />
                    <Line
                      type="monotone"
                      dataKey="branch"
                      name="Branch"
                      stroke="#f59e0b"
                      strokeWidth={2.5}
                      connectNulls
                    />
                    <Line
                      type="monotone"
                      dataKey="score"
                      name="Score"
                      stroke="#0f9f75"
                      strokeWidth={2.5}
                      connectNulls
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <p className="evolution-source-note">{evolution.message}</p>
            </div>
          </div>
        </>
      )}
    </section>
  );
}

export default function OptimizationRun() {
  const { runId = "" } = useParams<{ runId: string }>();
  const [, navigate] = useLocation();
  const { experiments } = useRepositories();
  const queryClient = useQueryClient();
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
    refetchInterval: (query) =>
      runQuery.data &&
      (optimizationRunIsActive(runQuery.data.status) || !query.state.data?.comparisonRunId)
        ? 3_000
        : false,
  });
  const evolutionQuery = useQuery({
    queryKey: ["optimization-runs", runId, "evolution"],
    queryFn: ({ signal }) => experiments.getOptimizationEvolution(runId, signal),
    enabled: runId !== "",
    refetchInterval: () =>
      runQuery.data && optimizationRunIsActive(runQuery.data.status) ? 3_000 : false,
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
  const cancel = useMutation({
    mutationFn: () => experiments.cancelOptimization(runId),
    onSuccess: (cancelledRun) => {
      queryClient.setQueryData(["optimization-runs", runId], cancelledRun);
      void queryClient.invalidateQueries({
        queryKey: ["experiments", cancelledRun.experimentId],
      });
      void queryClient.invalidateQueries({
        queryKey: ["optimization-runs", runId, "evolution"],
      });
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
  const baselinePrompt = experiment?.baselinePrompt ?? null;
  const finalPrompt = run.finalComparison
    ? run.finalComparison.promoted
      ? run.candidatePrompt
      : baselinePrompt
    : null;

  return (
    <div className="platform-page optimization-run-page">
      <button className="back-link" onClick={() => navigate("/experiments")}>
        ← Experiments
      </button>
      <PageHeader
        eyebrow={`Optimization run · ${run.id.slice(0, 8)}`}
        title={experiment?.name ?? "Prompt optimization"}
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
          <button
            className="danger-button stop-optimization-button"
            type="button"
            disabled={cancel.isPending}
            onClick={() => {
              if (
                window.confirm(
                  "Stop this optimization? The current candidate may be incomplete, but existing logs will be retained.",
                )
              ) {
                cancel.mutate();
              }
            }}
          >
            {cancel.isPending ? "Stopping…" : "Stop optimization"}
          </button>
        </section>
      )}

      {cancel.isError && (
        <section className="baseline-error" role="alert">
          <strong>Could not stop optimization</strong>
          <p>{cancel.error instanceof Error ? cancel.error.message : "Please try again."}</p>
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
            <strong>Baseline and optimized results are ready</strong>
            <p>
              GEPA used the baseline prompt as candidate zero and completed the locked paired
              comparison in the same cloud job.
            </p>
          </div>
          {experiment?.comparisonRunId ? (
            <StatusBadge tone="success">Paired evaluation complete</StatusBadge>
          ) : (
            <StatusBadge tone="info">Finalizing paired result…</StatusBadge>
          )}
        </section>
      )}

      <section className="platform-card optimization-results-card">
        <div className="card-heading optimization-results-heading">
          <div>
            <h2>Evaluation results</h2>
          </div>
          {run.finalComparison && (
            <StatusBadge tone={run.finalComparison.promoted ? "success" : "warning"}>
              {run.finalComparison.promoted ? "Promoted" : "Baseline retained"}
            </StatusBadge>
          )}
        </div>

        <div className="optimization-result-section">
          <div className="optimization-result-heading">
            <h3>Validation</h3>
          </div>
          <div className="platform-stats-grid baseline-metrics-grid">
            <StatCard
              label="Baseline"
              value={score(run.baselineValidationScore)}
              detail="Parent prompt"
            />
            <StatCard
              label="Candidate"
              value={score(run.candidateValidationScore)}
              detail="Best proposal"
              tone="violet"
            />
            <StatCard
              label="Gain"
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
        </div>

        {run.finalComparison && (
          <div className="optimization-result-section is-final">
            <div className="optimization-result-heading">
              <h3>Final locked test</h3>
            </div>
            <div className="platform-stats-grid baseline-metrics-grid">
              <StatCard
                label="Baseline"
                value={score(run.finalComparison.baselineMetrics.score)}
                detail="Candidate zero"
              />
              <StatCard
                label="Optimized"
                value={score(run.finalComparison.candidateMetrics.score)}
                detail="GEPA proposal"
                tone="violet"
              />
              <StatCard
                label="Gain"
                value={
                  run.finalComparison.absoluteGain === null
                    ? "—"
                    : `${run.finalComparison.absoluteGain >= 0 ? "+" : ""}${run.finalComparison.absoluteGain.toFixed(3)}`
                }
                detail="Optimized minus baseline"
                tone="green"
              />
              <StatCard
                label="Decision"
                value={run.finalComparison.promoted ? "Promote" : "Retain baseline"}
                detail={
                  run.finalComparison.skipped
                    ? run.finalComparison.reason || "Unchanged candidate"
                    : "Strict improvement required"
                }
                tone="orange"
              />
            </div>
          </div>
        )}
      </section>

      {evolutionQuery.data ? (
        <EvolutionPanel evolution={evolutionQuery.data} />
      ) : evolutionQuery.isError ? (
        <section className="platform-card evolution-card">
          <div className="empty-state" role="alert">
            Evolution logs could not be loaded. The optimization status will continue updating.
          </div>
        </section>
      ) : (
        <section className="platform-card evolution-card">
          <div className="evolution-empty" role="status">
            <span className="baseline-spinner" aria-hidden="true" />
            <div>
              <strong>Loading Cloud Run evolution log…</strong>
            </div>
          </div>
        </section>
      )}

      {run.id === "" && (
        <>
          <div className="platform-two-column optimization-details-grid">
            <section className="platform-card">
              <div className="card-heading">
                <div>
                  <h2>Prompt lineage</h2>
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
                </div>
                <StatusBadge tone={run.artifacts.length > 0 ? "success" : "neutral"}>
                  {run.artifacts.length} files
                </StatusBadge>
              </div>
              {run.artifacts.length === 0 ? (
                <div className="empty-state">
                  Artifacts will appear after optimization succeeds.
                </div>
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
                  {download.error instanceof Error
                    ? download.error.message
                    : "Could not download artifact."}
                </div>
              )}
            </section>
          </div>

          <div className="platform-two-column optimization-details-grid">
            <PromptCard
              title="Baseline prompt"
              description="The immutable candidate-zero prompt saved with this experiment."
              prompt={baselinePrompt}
              emptyMessage={
                experimentQuery.isPending
                  ? "Loading the baseline prompt…"
                  : "No baseline prompt snapshot is available."
              }
            />
            <PromptCard
              title="Final selected prompt"
              description={
                run.finalComparison?.promoted
                  ? "The optimized prompt passed the strict promotion gate."
                  : "The baseline was retained because the proposal did not strictly improve it."
              }
              prompt={finalPrompt}
              emptyMessage={
                active
                  ? "The final prompt will appear when optimization finishes."
                  : "No final prompt decision was published."
              }
            />
          </div>
        </>
      )}
    </div>
  );
}
