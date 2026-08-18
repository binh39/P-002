import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useLocation, useRoute } from "wouter";

import { useRepositories } from "@/app/providers";
import { PageHeader, StatCard, StatusBadge } from "@/components/PlatformUI";
import type { PromptBundle, PromptSnapshot } from "@/domain/experiments";

type PromptComponent = "initial" | "error";

function percentage(value: number | null) {
  return value === null ? "—" : `${(value * 100).toFixed(1)}%`;
}

function formatTimestamp(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(
    new Date(value),
  );
}

function finalPromptLabel(snapshot: PromptSnapshot | null) {
  if (!snapshot) return "Optimization pending";
  return snapshot.origin === "baseline_retained" ? "Baseline retained" : "Optimized prompt";
}

function diffLines(baseline: string, optimized: string) {
  const before = baseline.split("\n");
  const after = optimized.split("\n");
  const lines: string[] = [];
  for (let index = 0; index < Math.max(before.length, after.length); index += 1) {
    const beforeLine = before[index];
    const afterLine = after[index];
    if (beforeLine === afterLine) {
      if (beforeLine !== undefined) lines.push(`  ${beforeLine}`);
      continue;
    }
    if (beforeLine !== undefined) lines.push(`- ${beforeLine}`);
    if (afterLine !== undefined) lines.push(`+ ${afterLine}`);
  }
  return lines.join("\n");
}

function PromptMetadata({ snapshot }: { snapshot: PromptSnapshot }) {
  return (
    <dl className="definition-list prompt-registry-metadata">
      <div>
        <dt>Prompt digest</dt>
        <dd>
          <code>{snapshot.promptDigest}</code>
        </dd>
      </div>
      <div>
        <dt>Generation model</dt>
        <dd>
          <code>{snapshot.coverupModel}</code>
        </dd>
      </div>
      <div>
        <dt>Optimizer model</dt>
        <dd>
          <code>{snapshot.optimizeModel}</code>
        </dd>
      </div>
      <div>
        <dt>Dataset seed</dt>
        <dd>{snapshot.splitSeed}</dd>
      </div>
      <div>
        <dt>Runtime protocol</dt>
        <dd>v{snapshot.runnerProtocolVersion}</dd>
      </div>
    </dl>
  );
}

function PromptCode({
  title,
  prompt,
  component,
}: {
  title: string;
  prompt: PromptBundle;
  component: PromptComponent;
}) {
  return (
    <section className="platform-card prompt-registry-prompt-card">
      <div className="card-heading">
        <h2>{title}</h2>
      </div>
      <pre className="prompt-registry-code">
        <code>{prompt[component]}</code>
      </pre>
    </section>
  );
}

function PromptActions({ label }: { label: string }) {
  return (
    <button
      className="secondary-button"
      type="button"
      disabled
      title="Generate Test Cases will be enabled when the Final Test Generation backend is delivered."
    >
      {label}
    </button>
  );
}

function HeaderActions() {
  return (
    <div className="prompt-registry-header-actions">
      <PromptActions label="Generate baseline tests" />
      <PromptActions label="Generate final tests" />
    </div>
  );
}

export default function PromptRegistryDetail() {
  const [, params] = useRoute("/prompts/:experimentId");
  const [, navigate] = useLocation();
  const { promptRegistry } = useRepositories();
  const [component, setComponent] = useState<PromptComponent>("initial");
  const [view, setView] = useState<"side-by-side" | "diff">("side-by-side");
  const experimentId = params?.experimentId ?? "";
  const query = useQuery({
    queryKey: ["prompt-registry", experimentId],
    queryFn: ({ signal }) => promptRegistry.get(experimentId, signal),
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
        actions={<HeaderActions />}
      />

      <section className="platform-card prompt-registry-summary">
        <div className="card-heading">
          <div>
            <h2>Paired evaluation</h2>
            <p>Baseline and final prompt metrics use the same locked evaluation protocol.</p>
          </div>
          <StatusBadge tone={selected?.origin === "optimized_candidate" ? "success" : "warning"}>
            {finalPromptLabel(selected)}
          </StatusBadge>
        </div>
        <div className="platform-stats-grid baseline-metrics-grid">
          <StatCard
            label="Baseline score"
            value={percentage(entry.baselineMetrics.score)}
            detail="Locked baseline"
          />
          <StatCard
            label="Final prompt score"
            value={percentage(entry.optimizedMetrics.score)}
            detail={finalPromptLabel(selected)}
            tone="violet"
          />
          <StatCard
            label="Statement coverage"
            value={percentage(entry.optimizedMetrics.statementCoverage)}
            detail={`Baseline ${percentage(entry.baselineMetrics.statementCoverage)}`}
            tone="green"
          />
          <StatCard
            label="Branch coverage"
            value={percentage(entry.optimizedMetrics.branchCoverage)}
            detail={`Baseline ${percentage(entry.baselineMetrics.branchCoverage)}`}
            tone="orange"
          />
        </div>
      </section>

      <div className="prompt-registry-view-controls" aria-label="Prompt display controls">
        <div role="group" aria-label="Prompt component">
          {(["initial", "error"] as PromptComponent[]).map((value) => (
            <button
              key={value}
              className={component === value ? "is-selected" : ""}
              onClick={() => setComponent(value)}
            >
              {value === "initial" ? "Initial prompt" : "Error prompt"}
            </button>
          ))}
        </div>
        <div role="group" aria-label="Prompt comparison view">
          <button
            className={view === "side-by-side" ? "is-selected" : ""}
            onClick={() => setView("side-by-side")}
          >
            Side by side
          </button>
          <button className={view === "diff" ? "is-selected" : ""} onClick={() => setView("diff")}>
            Unified diff
          </button>
        </div>
      </div>

      {view === "side-by-side" ? (
        <div className="platform-two-column prompt-registry-prompt-grid">
          <PromptCode
            title="Baseline prompt"
            prompt={entry.baseline.prompt}
            component={component}
          />
          <PromptCode
            title={finalPromptLabel(selected)}
            prompt={selectedPrompt}
            component={component}
          />
        </div>
      ) : (
        <section className="platform-card prompt-registry-diff-card">
          <div className="card-heading">
            <h2>{component === "initial" ? "Initial prompt diff" : "Error prompt diff"}</h2>
          </div>
          <pre className="prompt-registry-code prompt-registry-unified-diff">
            <code>{diffLines(entry.baseline.prompt[component], selectedPrompt[component])}</code>
          </pre>
        </section>
      )}

      <div className="platform-two-column prompt-registry-prompt-grid">
        <section className="platform-card">
          <div className="card-heading">
            <h2>Baseline context</h2>
          </div>
          <PromptMetadata snapshot={entry.baseline} />
        </section>
        {selected && (
          <section className="platform-card">
            <div className="card-heading">
              <h2>{finalPromptLabel(selected)} context</h2>
            </div>
            <PromptMetadata snapshot={selected} />
          </section>
        )}
      </div>
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
