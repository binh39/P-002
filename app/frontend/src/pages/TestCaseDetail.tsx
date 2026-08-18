import { useMutation, useQuery } from "@tanstack/react-query";
import { useLocation, useRoute } from "wouter";

import { useRepositories } from "@/app/providers";
import { PageHeader, StatCard, StatusBadge } from "@/components/PlatformUI";
import type { TestGenerationStatus } from "@/domain/experiments";

const activeStatuses: TestGenerationStatus[] = [
  "queued",
  "preparing",
  "generating",
  "running_tests",
];

function percentage(value: number | null) {
  return value === null ? "—" : `${(value * 100).toFixed(1)}%`;
}

function formatStatus(status: TestGenerationStatus) {
  return status.replace(/_/g, " ").replace(/^./, (character) => character.toUpperCase());
}

function statusTone(status: TestGenerationStatus) {
  if (status === "completed") return "success" as const;
  if (["failed", "cancelled", "timed_out"].includes(status)) return "danger" as const;
  if (status === "partial") return "warning" as const;
  return "info" as const;
}

function formatCost(value: number) {
  return new Intl.NumberFormat(undefined, { style: "currency", currency: "USD" }).format(value);
}

export default function TestCaseDetail() {
  const [, params] = useRoute("/test-cases/:runId");
  const [, navigate] = useLocation();
  const { testGeneration } = useRepositories();
  const runId = params?.runId ?? "";
  const query = useQuery({
    queryKey: ["test-generation-runs", runId],
    queryFn: ({ signal }) => testGeneration.get(runId, signal),
    enabled: runId !== "",
    refetchInterval: (current) =>
      current.state.data && activeStatuses.includes(current.state.data.status) ? 3_000 : false,
  });
  const download = useMutation({
    mutationFn: async (artifactName: string) => ({
      artifactName,
      blob: await testGeneration.downloadArtifact(runId, artifactName),
    }),
    onSuccess: ({ artifactName, blob }) => {
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download =
        artifactName === "suite_zip" ? "generated-tests.zip" : "test-generation-manifest.json";
      anchor.click();
      URL.revokeObjectURL(url);
    },
  });

  if (query.isPending) {
    return (
      <div className="page-state" role="status">
        Loading final test run…
      </div>
    );
  }
  if (query.isError || !query.data) {
    return (
      <div className="page-state page-state-error" role="alert">
        <h2>Test run is unavailable</h2>
        <p>
          {query.error instanceof Error
            ? query.error.message
            : "The requested test run was not found."}
        </p>
        <button onClick={() => navigate("/test-cases")}>Back to Test Cases</button>
      </div>
    );
  }

  const run = query.data;
  const artifacts = Object.keys(run.artifactObjects);
  return (
    <div className="platform-page test-case-detail-page">
      <button className="back-link" onClick={() => navigate("/test-cases")}>
        ← Test Cases
      </button>
      <PageHeader
        eyebrow={`Experiment · ${run.experimentId}`}
        title={run.promptRole === "baseline" ? "Baseline test suite" : "Final prompt test suite"}
        description={`Run ${run.id}`}
        actions={
          <StatusBadge tone={statusTone(run.status)}>{formatStatus(run.status)}</StatusBadge>
        }
      />
      {run.errorMessage && (
        <section className="prompt-registry-generation-notice is-error" role="alert">
          {run.errorMessage}
        </section>
      )}
      <div className="platform-stats-grid">
        <StatCard
          label="Project statement"
          value={percentage(run.metrics.projectStatementCoverage)}
        />
        <StatCard
          label="Project branch"
          value={percentage(run.metrics.projectBranchCoverage)}
          tone="orange"
        />
        <StatCard label="Target score" value={percentage(run.metrics.targetScore)} tone="violet" />
        <StatCard label="Estimated cost" value={formatCost(run.estimatedCostUsd)} tone="green" />
      </div>
      <div className="platform-two-column prompt-registry-prompt-grid">
        <section className="platform-card">
          <div className="card-heading">
            <h2>Immutable snapshot</h2>
          </div>
          <dl className="definition-list prompt-registry-metadata">
            <div>
              <dt>Prompt snapshot</dt>
              <dd>
                <code>{run.promptSnapshotId}</code>
              </dd>
            </div>
            <div>
              <dt>Prompt digest</dt>
              <dd>
                <code>{run.promptDigest}</code>
              </dd>
            </div>
            <div>
              <dt>Source snapshot</dt>
              <dd>
                <code>{run.sourceSnapshotDigest}</code>
              </dd>
            </div>
            <div>
              <dt>Dataset digest</dt>
              <dd>
                <code>{run.datasetDigest}</code>
              </dd>
            </div>
            <div>
              <dt>Projects</dt>
              <dd>{run.projectIds.join(", ")}</dd>
            </div>
          </dl>
        </section>
        <section className="platform-card">
          <div className="card-heading">
            <h2>Generation configuration</h2>
          </div>
          <dl className="definition-list prompt-registry-metadata">
            <div>
              <dt>Model</dt>
              <dd>
                <code>{run.model}</code>
              </dd>
            </div>
            <div>
              <dt>Scope</dt>
              <dd>
                {run.scope} · {run.targetIds.length} targets
              </dd>
            </div>
            <div>
              <dt>Seed</dt>
              <dd>{run.randomSeed}</dd>
            </div>
            <div>
              <dt>Attempts / repeat</dt>
              <dd>
                {run.maxAttempts} / {run.repeatTests}
              </dd>
            </div>
            <div>
              <dt>Concurrency / rate</dt>
              <dd>
                {run.maxConcurrency} / {run.rateLimit ?? "default"}
              </dd>
            </div>
            <div>
              <dt>Runner protocol</dt>
              <dd>v{run.runnerProtocolVersion}</dd>
            </div>
          </dl>
        </section>
      </div>
      <section className="platform-card">
        <div className="card-heading">
          <div>
            <h2>Suite results</h2>
            <p>Final-suite coverage is distinct from target-only coverage.</p>
          </div>
        </div>
        <div className="platform-stats-grid baseline-metrics-grid">
          <StatCard
            label="Tests"
            value={run.metrics.testCount}
            detail={`${run.metrics.testFileCount} files`}
          />
          <StatCard
            label="Passed"
            value={run.metrics.passed ?? "—"}
            detail={`${run.metrics.failed ?? "—"} failed`}
            tone="green"
          />
          <StatCard
            label="Target statement"
            value={percentage(run.metrics.targetStatementCoverage)}
            detail={`${run.metrics.completedTargetCount}/${run.metrics.targetCount} targets`}
            tone="violet"
          />
          <StatCard
            label="Target branch"
            value={percentage(run.metrics.targetBranchCoverage)}
            detail={`${run.metrics.failedTargetCount} failed targets`}
            tone="orange"
          />
        </div>
      </section>
      <section className="platform-card">
        <div className="card-heading">
          <div>
            <h2>Artifacts</h2>
            <p>
              Files are downloaded through the owner-scoped API; no long-lived signed URL is stored
              in the browser.
            </p>
          </div>
        </div>
        {artifacts.length === 0 ? (
          <div className="empty-state">Artifacts appear when the runner completes.</div>
        ) : (
          <div className="prompt-registry-header-actions">
            {artifacts.map((artifactName) => (
              <button
                key={artifactName}
                className="secondary-button"
                disabled={download.isPending}
                onClick={() => download.mutate(artifactName)}
              >
                {download.isPending && download.variables === artifactName
                  ? "Downloading…"
                  : artifactName === "suite_zip"
                    ? "Download suite ZIP"
                    : "Download manifest"}
              </button>
            ))}
          </div>
        )}
        {download.isError && (
          <p className="inline-validation-error" role="alert">
            {download.error instanceof Error ? download.error.message : "Artifact download failed."}
          </p>
        )}
      </section>
    </div>
  );
}
