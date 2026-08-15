import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocation } from "wouter";

import { useRepositories } from "@/app/providers";
import { PageHeader, StatCard, StatusBadge } from "@/components/PlatformUI";
import type { PromptBundle, PromptVersion, PromptVersionStatus } from "@/domain/experiments";

function formatTimestamp(value: string | null) {
  return value
    ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(
        new Date(value),
      )
    : "Not reviewed";
}

function statusTone(status: PromptVersionStatus) {
  if (status === "approved") return "success" as const;
  if (status === "rejected") return "danger" as const;
  return "warning" as const;
}

function statusLabel(status: PromptVersionStatus) {
  if (status === "in_review") return "Awaiting review";
  return status[0].toUpperCase() + status.slice(1);
}

function PromptParts({ prompt }: { prompt: PromptBundle | Record<string, string> | null }) {
  if (!prompt) {
    return <div className="empty-state">No prompt snapshot is available.</div>;
  }

  return (
    <div className="review-prompt-parts">
      <section>
        <h4>Initial</h4>
        <pre>{prompt.initial || "No initial prompt content was recorded."}</pre>
      </section>
      <section>
        <h4>Error</h4>
        <pre>{prompt.error || "No error prompt content was recorded."}</pre>
      </section>
    </div>
  );
}

export default function ReviewApproval() {
  const { experiments, promptVersions } = useRepositories();
  const queryClient = useQueryClient();
  const [location, navigate] = useLocation();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [comment, setComment] = useState("");
  const requestedId = new URLSearchParams(location.split("?")[1] ?? "").get("versionId");

  const versionsQuery = useQuery({
    queryKey: ["prompt-versions"],
    queryFn: ({ signal }) => promptVersions.list(undefined, signal),
  });
  const experimentQuery = useQuery({
    queryKey: ["experiments"],
    queryFn: ({ signal }) => experiments.list(signal),
  });
  const versions = useMemo(() => versionsQuery.data?.items ?? [], [versionsQuery.data]);
  const selected = useMemo(
    () => versions.find((item) => item.id === (selectedId ?? requestedId)) ?? versions[0] ?? null,
    [requestedId, selectedId, versions],
  );
  const selectedExperiment = experimentQuery.data?.find(
    (item) => item.id === selected?.experimentId,
  );
  const comparisonQuery = useQuery({
    queryKey: ["comparison-runs", selected?.comparisonRunId],
    queryFn: ({ signal }) => experiments.getComparisonRun(selected?.comparisonRunId ?? "", signal),
    enabled: Boolean(selected?.comparisonRunId),
  });

  const review = useMutation({
    mutationFn: ({
      version,
      decision,
    }: {
      version: PromptVersion;
      decision: "approve" | "reject";
    }) => promptVersions.review(version.id, decision, comment.trim()),
    onSuccess: async (version) => {
      setComment(version.reviewComment);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["prompt-versions"] }),
        queryClient.invalidateQueries({ queryKey: ["experiments"] }),
        queryClient.invalidateQueries({ queryKey: ["comparison-runs", version.comparisonRunId] }),
      ]);
    },
  });

  if (versionsQuery.isPending || experimentQuery.isPending) {
    return (
      <div className="page-state" role="status">
        Loading prompt review queue…
      </div>
    );
  }
  if (versionsQuery.isError || experimentQuery.isError) {
    const error = versionsQuery.error ?? experimentQuery.error;
    return (
      <div className="page-state page-state-error" role="alert">
        <h2>Prompt review is unavailable</h2>
        <p>{error instanceof Error ? error.message : "An unexpected error occurred."}</p>
        <button
          onClick={() => void Promise.all([versionsQuery.refetch(), experimentQuery.refetch()])}
        >
          Try again
        </button>
      </div>
    );
  }
  if (!selected) {
    return (
      <div className="platform-page">
        <PageHeader
          eyebrow="Prompt registry"
          title="Review & Approval"
          description="Eligible optimized prompts will appear here after paired comparison."
        />
        <section className="platform-card empty-state">
          No prompt versions are awaiting or have completed review for this workspace.
        </section>
      </div>
    );
  }

  const comparison = comparisonQuery.data;
  const canReview = selected.status === "in_review" && !review.isPending;
  return (
    <div className="platform-page">
      <PageHeader
        eyebrow="Prompt registry"
        title="Review & Approval"
        description="Approve only candidates that passed the immutable paired evaluation protocol."
        actions={
          <StatusBadge tone={statusTone(selected.status)}>
            {statusLabel(selected.status)}
          </StatusBadge>
        }
      />

      <div className="platform-two-column comparison-details-grid">
        <section className="platform-card table-card">
          <div className="card-heading">
            <div>
              <h2>Review queue</h2>
              <p>
                {versions.length} prompt version{versions.length === 1 ? "" : "s"} owned by you.
              </p>
            </div>
          </div>
          <div className="artifact-list">
            {versions.map((version) => (
              <button
                className="table-action"
                key={version.id}
                onClick={() => {
                  setSelectedId(version.id);
                  setComment(version.reviewComment);
                }}
                aria-pressed={version.id === selected.id}
              >
                <span>
                  <strong>
                    {experimentQuery.data?.find((item) => item.id === version.experimentId)?.name ??
                      `Experiment ${version.experimentId.slice(0, 8)}`}
                  </strong>
                  <small>
                    {version.id.slice(0, 8)} · {formatTimestamp(version.createdAt)}
                  </small>
                </span>
                <StatusBadge tone={statusTone(version.status)}>
                  {statusLabel(version.status)}
                </StatusBadge>
              </button>
            ))}
          </div>
        </section>

        <section className="platform-card">
          <div className="card-heading">
            <div>
              <h2>{selectedExperiment?.name ?? "Prompt version"}</h2>
              <p>
                Version {selected.id.slice(0, 8)} · created {formatTimestamp(selected.createdAt)}
              </p>
            </div>
          </div>
          <div className="platform-stats-grid baseline-metrics-grid">
            <StatCard
              label="Baseline score"
              value={comparison?.baselineMetrics.score?.toFixed(3) ?? "—"}
              detail="Locked split"
            />
            <StatCard
              label="Candidate score"
              value={comparison?.candidateMetrics.score?.toFixed(3) ?? "—"}
              detail="Final evaluation"
              tone="violet"
            />
            <StatCard
              label="Absolute gain"
              value={
                comparison?.absoluteGain === null || comparison?.absoluteGain === undefined
                  ? "—"
                  : `${comparison.absoluteGain >= 0 ? "+" : ""}${comparison.absoluteGain.toFixed(3)}`
              }
              detail="Candidate − baseline"
              tone="green"
            />
          </div>
          {comparisonQuery.isError && (
            <p className="auth-error">Comparison details could not be loaded.</p>
          )}
          {comparison && (
            <button
              className="table-action"
              onClick={() => navigate(`/comparison-runs/${comparison.id}`)}
            >
              Open paired comparison
            </button>
          )}
        </section>
      </div>

      <section className="platform-card comparison-details-grid review-prompt-card">
        <div className="card-heading">
          <div>
            <h2>Prompt comparison</h2>
            <p>Compare the immutable baseline and candidate by prompt component.</p>
          </div>
        </div>
        <div className="review-prompt-comparison">
          <article className="review-prompt-column">
            <header>
              <h3>Baseline prompt</h3>
              <span>Candidate zero</span>
            </header>
            <PromptParts prompt={selectedExperiment?.baselinePrompt ?? null} />
          </article>
          <article className="review-prompt-column is-candidate">
            <header>
              <h3>Candidate prompt</h3>
              <span>Proposed version</span>
            </header>
            <PromptParts prompt={selected.prompt} />
          </article>
        </div>
      </section>

      <section className="platform-card comparison-details-grid">
        <div className="card-heading">
          <div>
            <h2>Prompt lineage</h2>
            <p>Digests identify the immutable prompt pair.</p>
          </div>
        </div>
        <dl className="definition-list comparison-definition-list">
          <div>
            <dt>Baseline digest</dt>
            <dd>
              <code>{selected.parentPromptDigest}</code>
            </dd>
          </div>
          <div>
            <dt>Candidate digest</dt>
            <dd>
              <code>{selected.promptDigest}</code>
            </dd>
          </div>
          <div>
            <dt>Review state</dt>
            <dd>{statusLabel(selected.status)}</dd>
          </div>
          <div>
            <dt>Reviewed at</dt>
            <dd>{formatTimestamp(selected.reviewedAt)}</dd>
          </div>
          {selected.reviewerId && (
            <div>
              <dt>Reviewer</dt>
              <dd>
                <code>{selected.reviewerId}</code>
              </dd>
            </div>
          )}
        </dl>
      </section>

      <section className="platform-card">
        <div className="card-heading">
          <div>
            <h2>Decision</h2>
            <p>Review decisions are final. A repeated request for the same decision is safe.</p>
          </div>
        </div>
        <label className="platform-field">
          <span>Review comment (optional)</span>
          <textarea
            value={comment}
            disabled={!canReview}
            onChange={(event) => setComment(event.target.value)}
            rows={3}
            maxLength={1000}
            placeholder="Explain this decision for your team…"
          />
        </label>
        {selected.status === "in_review" ? (
          <div className="platform-header-actions">
            <button
              className="primary-button"
              disabled={!canReview}
              onClick={() => review.mutate({ version: selected, decision: "approve" })}
            >
              Approve prompt
            </button>
            <button
              className="secondary-button"
              disabled={!canReview}
              onClick={() => review.mutate({ version: selected, decision: "reject" })}
            >
              Reject prompt
            </button>
          </div>
        ) : (
          <div className="empty-state">
            This prompt was {selected.status}.{" "}
            {selected.reviewComment && `Comment: ${selected.reviewComment}`}
          </div>
        )}
        {review.isError && (
          <p className="auth-error" role="alert">
            {review.error instanceof Error
              ? review.error.message
              : "Unable to save the review decision."}
          </p>
        )}
      </section>
    </div>
  );
}
