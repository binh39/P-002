import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useLocation, useRoute } from "wouter";

import { ApiError, apiDownload } from "@/api/client";
import { useRepositories } from "@/app/providers";
import { PageHeader, StatusBadge } from "@/components/PlatformUI";
import type { PromptBundle } from "@/domain/experiments";

function percentage(value: number | null) {
  return value === null ? "â€”" : `${(value * 100).toFixed(1)}%`;
}

function PromptPanel({ title, prompt }: { title: string; prompt: PromptBundle }) {
  return (
    <section className="platform-card prompt-registry-prompt-card">
      <h2>{title}</h2>
      {(["initial", "error", "missing_coverage"] as const).map((part) =>
        prompt[part] ? (
          <section key={part}>
            <h3>{part.replace("_", " ")}</h3>
            <pre className="prompt-registry-code">
              <code>{prompt[part]}</code>
            </pre>
          </section>
        ) : null,
      )}
    </section>
  );
}

async function downloadArtifact(versionId: string, artifactName: string) {
  const blob = await apiDownload(
    `/reviews/${versionId}/artifacts/${encodeURIComponent(artifactName)}`,
  );
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = artifactName;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function ReviewDetail() {
  const [, params] = useRoute("/reviews/:versionId");
  const [, navigate] = useLocation();
  const queryClient = useQueryClient();
  const { promptVersions } = useRepositories();
  const versionId = params?.versionId ?? "";
  const [comment, setComment] = useState("");
  const [decision, setDecision] = useState<"approve" | "reject" | null>(null);
  const query = useQuery({
    queryKey: ["review", versionId],
    queryFn: ({ signal }) => promptVersions.getReview(versionId, signal),
    enabled: Boolean(versionId),
  });
  const mutation = useMutation({
    mutationFn: async () => {
      if (!decision) throw new Error("Choose a review decision");
      if (decision === "reject" && !comment.trim())
        throw new Error("A rejection comment is required");
      return promptVersions.review(versionId, decision, comment);
    },
    onSuccess: async () => {
      setDecision(null);
      await queryClient.invalidateQueries({ queryKey: ["review", versionId] });
      await queryClient.invalidateQueries({ queryKey: ["reviews"] });
    },
    onError: async (error) => {
      if (error instanceof ApiError && error.status === 409) {
        await queryClient.invalidateQueries({ queryKey: ["review", versionId] });
      }
    },
  });
  if (query.isPending)
    return (
      <div className="page-state" role="status">
        Loading review evidenceâ€¦
      </div>
    );
  if (query.isError)
    return (
      <div className="page-state page-state-error" role="alert">
        {query.error.message}
      </div>
    );
  const { version, comparison } = query.data;
  return (
    <div className="platform-page prompt-registry-detail-page">
      <button className="back-link" onClick={() => navigate("/reviews")}>
        â† Review Queue
      </button>
      <PageHeader
        eyebrow={`Candidate Â· ${version.id}`}
        title={query.data.experimentName}
        description={`Created by ${query.data.creatorId} Â· locked comparison evidence`}
      />
      <section className="platform-card prompt-registry-summary">
        <div className="card-heading">
          <h2>Promotion evidence</h2>
          <StatusBadge tone={comparison.promotionEligible ? "success" : "danger"}>
            {comparison.promotionEligible ? "Promotion eligible" : "Not eligible"}
          </StatusBadge>
        </div>
        <dl className="definition-list prompt-registry-settings-list">
          <div>
            <dt>Final split gain</dt>
            <dd>{percentage(comparison.absoluteGain)}</dd>
          </div>
          <div>
            <dt>Baseline score</dt>
            <dd>{percentage(comparison.baselineMetrics.score)}</dd>
          </div>
          <div>
            <dt>Candidate score</dt>
            <dd>{percentage(comparison.candidateMetrics.score)}</dd>
          </div>
          <div>
            <dt>Replicates</dt>
            <dd>{comparison.replicateCount}</dd>
          </div>
          <div>
            <dt>Decision reason</dt>
            <dd>{comparison.decisionReason}</dd>
          </div>
        </dl>
      </section>
      <div className="platform-two-column prompt-registry-prompt-grid">
        <PromptPanel title="Baseline" prompt={query.data.baselinePrompt} />
        <PromptPanel title="Candidate" prompt={query.data.candidatePrompt} />
      </div>
      <section className="platform-card">
        <h2>Review artifacts</h2>
        {query.data.artifactNames.length === 0 ? (
          <p>No downloadable artifacts.</p>
        ) : (
          <div className="delete-dialog-actions">
            {query.data.artifactNames.map((name) => (
              <button
                className="secondary-button"
                key={name}
                onClick={() => void downloadArtifact(versionId, name)}
              >
                {name}
              </button>
            ))}
          </div>
        )}
      </section>
      {version.status === "in_review" ? (
        <section className="platform-card">
          <h2>Decision</h2>
          <textarea
            aria-label="Review comment"
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            placeholder="Required when rejecting"
          />
          <div className="delete-dialog-actions">
            <button className="secondary-button" onClick={() => setDecision("reject")}>
              Reject
            </button>
            <button className="primary-button" onClick={() => setDecision("approve")}>
              Approve
            </button>
          </div>
          {decision && (
            <div role="dialog" aria-modal="true" className="platform-callout">
              <p>Confirm {decision}?</p>
              <button onClick={() => setDecision(null)}>Cancel</button>
              <button onClick={() => mutation.mutate()} disabled={mutation.isPending}>
                Confirm
              </button>
            </div>
          )}
          {mutation.isError && (
            <div className="inline-validation-error" role="alert">
              {mutation.error.message}
            </div>
          )}
        </section>
      ) : (
        <section className="platform-card">
          <StatusBadge tone={version.status === "rejected" ? "danger" : "success"}>
            {version.status}
          </StatusBadge>
          <p>{version.reviewComment || "No review comment."}</p>
        </section>
      )}
    </div>
  );
}
