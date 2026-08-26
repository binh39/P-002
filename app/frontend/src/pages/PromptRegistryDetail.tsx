import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useLocation, useRoute } from "wouter";

import { useRepositories } from "@/app/providers";
import { PageHeader } from "@/components/PlatformUI";
import type { Experiment, PromptCoverageMetrics, PromptBundle } from "@/domain/experiments";

function percentage(value: number | null) {
  return value === null ? "—" : `${(value * 100).toFixed(1)}%`;
}

function formatTimestamp(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(
    new Date(value),
  );
}

function progressWidth(value: number | null) {
  return `${Math.round(Math.max(0, Math.min(1, value ?? 0)) * 100)}%`;
}

function MetricBar({
  value,
  tone,
}: {
  value: number | null;
  tone: "baseline" | "final" | "statement" | "branch";
}) {
  return (
    <span className={`prompt-registry-metric-bar is-${tone}`} aria-hidden="true">
      <span style={{ width: progressWidth(value) }} />
    </span>
  );
}

function MetricDelta({ value, baseline }: { value: number | null; baseline?: number | null }) {
  if (baseline === undefined || value === null || baseline === null) return null;
  const delta = value - baseline;
  if (delta === 0) return null;
  const increased = delta > 0;
  return (
    <span
      className={`prompt-registry-metric-delta ${increased ? "is-positive" : "is-negative"}`}
      aria-label={`${increased ? "Increased" : "Decreased"} by ${Math.abs(delta * 100).toFixed(1)} percentage points`}
    >
      <span aria-hidden="true">{increased ? "↑" : "↓"}</span> {Math.abs(delta * 100).toFixed(1)}%
    </span>
  );
}

function MetricPanel({
  title,
  metrics,
  tone,
  comparison,
}: {
  title: string;
  metrics: PromptCoverageMetrics;
  tone: "baseline" | "final";
  comparison?: PromptCoverageMetrics;
}) {
  return (
    <section className={`prompt-registry-metric-panel is-${tone}`}>
      <h2>{title}</h2>
      <div className="prompt-registry-primary-score">
        <span>Score</span>
        <span className="prompt-registry-metric-value">
          <MetricDelta value={metrics.score} baseline={comparison?.score} />
          <strong>{percentage(metrics.score)}</strong>
        </span>
      </div>
      <MetricBar value={metrics.score} tone={tone} />
      <div className="prompt-registry-coverage-list">
        <div>
          <span>Statement coverage</span>
          <span className="prompt-registry-metric-value">
            <MetricDelta
              value={metrics.statementCoverage}
              baseline={comparison?.statementCoverage}
            />
            <strong>{percentage(metrics.statementCoverage)}</strong>
          </span>
          <MetricBar value={metrics.statementCoverage} tone="statement" />
        </div>
        <div>
          <span>Branch coverage</span>
          <span className="prompt-registry-metric-value">
            <MetricDelta value={metrics.branchCoverage} baseline={comparison?.branchCoverage} />
            <strong>{percentage(metrics.branchCoverage)}</strong>
          </span>
          <MetricBar value={metrics.branchCoverage} tone="branch" />
        </div>
      </div>
    </section>
  );
}

function PromptCode({
  title,
  prompt,
  action,
}: {
  title: string;
  prompt: PromptBundle;
  action?: ReactNode;
}) {
  return (
    <section className="platform-card prompt-registry-prompt-card">
      <div className="card-heading">
        <h2>{title}</h2>
        {action}
      </div>
      <div className="prompt-registry-prompt-parts">
        <section>
          <h3>Initial prompt</h3>
          <pre className="prompt-registry-code">
            <code>{prompt.initial}</code>
          </pre>
        </section>
        <section>
          <h3>Error prompt</h3>
          <pre className="prompt-registry-code">
            <code>{prompt.error}</code>
          </pre>
        </section>
        {prompt.missing_coverage && (
          <section>
            <h3>Missing coverage prompt</h3>
            <pre className="prompt-registry-code">
              <code>{prompt.missing_coverage}</code>
            </pre>
          </section>
        )}
      </div>
    </section>
  );
}

const samplingLabels: Record<Experiment["samplingMethod"], string> = {
  random: "Random",
  most_branches: "Most branches",
  most_statements: "Most statements",
  manual: "Manual selection",
};

function ExperimentSettings({ experiment }: { experiment: Experiment }) {
  const { settings, splitPercentages } = experiment;
  const values: Array<[string, string]> = [
    ["Environment", "Cloud Run isolated runner"],
    ["Function selection", samplingLabels[experiment.samplingMethod]],
    ["Functions", String(experiment.targetFunctionIds.length)],
    ["Random seed", String(experiment.splitSeed)],
    [
      "Dataset split",
      `${splitPercentages.train}% train / ${splitPercentages.validation}% valid / ${splitPercentages.test}% test`,
    ],
    ["CoverUp model", settings.coverupModel],
    ["Optimize model", settings.optimizeModel],
    [
      "CoverUp",
      `${settings.maxAttempts} attempts · ${settings.repeatTests} repeats · concurrency ${settings.maxConcurrency}`,
    ],
    ["Rate limit", settings.rateLimit === null ? "Default" : `${settings.rateLimit} requests/min`],
    [
      "GEPA budget",
      `${settings.maxMetricCalls} metric calls · ${settings.evaluationReplicates} replicate(s)`,
    ],
    ["Reflection minibatch size", String(settings.reflectionMinibatchSize)],
    ["Reflection temperature", String(settings.reflectionTemperature)],
    ["Pytest arguments", settings.pytestArgs || "Default"],
  ];
  return (
    <section className="platform-card prompt-registry-settings-card">
      <div className="card-heading">
        <h2>Experiment settings</h2>
      </div>
      <dl className="definition-list prompt-registry-settings-list">
        {values.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd title={value}>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function PromptActions({
  label,
  disabled,
  onClick,
  title,
}: {
  label: string;
  disabled: boolean;
  onClick: () => void;
  title?: string;
}) {
  return (
    <button
      className="secondary-button"
      type="button"
      disabled={disabled}
      onClick={onClick}
      title={title}
    >
      {label}
    </button>
  );
}

export default function PromptRegistryDetail() {
  const [, params] = useRoute("/prompts/:experimentId");
  const [, navigate] = useLocation();
  const { promptRegistry, experiments } = useRepositories();
  const experimentId = params?.experimentId ?? "";
  const query = useQuery({
    queryKey: ["prompt-registry", experimentId],
    queryFn: ({ signal }) => promptRegistry.get(experimentId, signal),
    enabled: experimentId !== "",
  });
  const experimentQuery = useQuery({
    queryKey: ["experiments", experimentId],
    queryFn: ({ signal }) => experiments.get(experimentId, signal),
    enabled: experimentId !== "",
  });
  if (query.isPending) {
    return (
      <div className="page-state" role="status">
        Loading prompt details…
      </div>
    );
  }
  if (query.isError || !query.data) {
    return (
      <div className="page-state page-state-error" role="alert">
        <h2>Prompt details are unavailable</h2>
        <p>
          {query.error instanceof Error
            ? query.error.message
            : "The requested experiment was not found."}
        </p>
        <button onClick={() => navigate("/prompts")}>Back to Prompt Registry</button>
      </div>
    );
  }

  const entry = query.data;
  const selected = entry.optimized;
  const selectedPrompt = selected?.prompt ?? entry.baseline.prompt;

  return (
    <div className="platform-page prompt-registry-detail-page">
      <button className="back-link" onClick={() => navigate("/prompts")}>
        ← Prompt Registry
      </button>
      <PageHeader
        eyebrow={`Experiment · ${entry.experimentId}`}
        title={entry.experimentName}
        description={`${entry.projectNames.join(", ") || entry.projectIds.join(", ")} · final prompt snapshots`}
      />

      <section className="platform-card prompt-registry-summary">
        <div className="prompt-registry-metric-comparison">
          <MetricPanel title="Baseline" metrics={entry.baselineMetrics} tone="baseline" />
          <MetricPanel
            title="Final Prompt"
            metrics={entry.optimizedMetrics}
            tone="final"
            comparison={entry.baselineMetrics}
          />
        </div>
      </section>

      <div className="platform-two-column prompt-registry-prompt-grid">
        <PromptCode
          title="Baseline prompt"
          prompt={entry.baseline.prompt}
          action={
            <PromptActions
              label="Generate Tests"
              disabled={false}
              onClick={() =>
                navigate(
                  `/test-suites/new?experiment=${encodeURIComponent(experimentId)}&prompt=baseline`,
                )
              }
            />
          }
        />
        <PromptCode
          title="Final Prompt"
          prompt={selectedPrompt}
          action={
            <PromptActions
              label="Generate Tests"
              disabled={selected === null}
              onClick={() =>
                navigate(
                  `/test-suites/new?experiment=${encodeURIComponent(experimentId)}&prompt=optimized`,
                )
              }
              title={
                selected === null
                  ? "Complete the final comparison before generating final tests."
                  : undefined
              }
            />
          }
        />
      </div>
      {experimentQuery.data && <ExperimentSettings experiment={experimentQuery.data} />}
      {!selected && (
        <section className="platform-card empty-state">
          Final prompt details will appear after optimization and the locked comparison finish.
        </section>
      )}
      <small className="prompt-registry-updated">
        Registry updated {formatTimestamp(entry.updatedAt)}
      </small>
    </div>
  );
}
