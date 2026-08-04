"use client";

import { FormEvent, useMemo, useState } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

type Experiment = {
  id: string;
  name: string;
  status: string;
  budget_limit: number;
  error_message: string | null;
};

type Candidate = {
  id: string;
  generation: number;
  prompt_text: string;
  fitness_score: number;
  pass_rate: number;
  statement_coverage: number;
  branch_coverage: number;
  cost_usd: number;
  latency_seconds: number;
  status: string;
};

const initialForm = {
  name: "isort prompt optimization",
  baseline_prompt:
    "eval/prompt_optimization/prompts/gpt_v2_baseline.json",
  module_path: "src/sample_repo/isort/isort",
  dataset_path: "eval/prompt_optimization/datasets/isort_symbols.jsonl",
  source_root: "src/sample_repo/isort",
  budget_limit: 5,
};

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function signedPercent(value: number) {
  const rounded = Math.round(value * 100);
  return `${rounded >= 0 ? "+" : ""}${rounded}%`;
}

function strategyName(candidate: Candidate) {
  return candidate.generation === 0 ? "CoverUp baseline" : "GEPA optimized";
}

export default function Home() {
  const [form, setForm] = useState(initialForm);
  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [experimentId, setExperimentId] = useState("");
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [reviewer, setReviewer] = useState("reviewer@example.com");
  const [comment, setComment] = useState("");
  const [message, setMessage] = useState("Ready to create an experiment.");
  const [busy, setBusy] = useState(false);

  const best = useMemo(
    () =>
      [...candidates].sort(
        (left, right) => right.fitness_score - left.fitness_score,
      )[0],
    [candidates],
  );
  const baseline = useMemo(
    () =>
      [...candidates]
        .filter((candidate) => candidate.generation === 0)
        .sort((left, right) => right.fitness_score - left.fitness_score)[0],
    [candidates],
  );
  const regressionMetrics = useMemo(() => {
    if (!best || !baseline || best.id === baseline.id) return [];
    return [
      ["Valid targets", best.pass_rate - baseline.pass_rate],
      ["Statement coverage", best.statement_coverage - baseline.statement_coverage],
      ["Branch coverage", best.branch_coverage - baseline.branch_coverage],
    ].filter(([, delta]) => Number(delta) < 0);
  }, [best, baseline]);
  async function request<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...options?.headers },
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail ?? `Request failed (${response.status})`);
    }
    return response.json();
  }

  async function createExperiment(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      const created = await request<Experiment>("/experiments", {
        method: "POST",
        body: JSON.stringify(form),
      });
      setExperiment(created);
      setExperimentId(created.id);
      setCandidates([]);
      setMessage("Experiment created. Start optimization when ready.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to create experiment.");
    } finally {
      setBusy(false);
    }
  }

  async function refresh() {
    if (!experimentId) return;
    setBusy(true);
    try {
      const [current, rows] = await Promise.all([
        request<Experiment>(`/experiments/${experimentId}`),
        request<Candidate[]>(`/experiments/${experimentId}/candidates`),
      ]);
      setExperiment(current);
      setCandidates(rows);
      setMessage(`Loaded ${rows.length} candidate${rows.length === 1 ? "" : "s"}.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to refresh.");
    } finally {
      setBusy(false);
    }
  }

  async function runOptimization() {
    if (!experimentId) return;
    setBusy(true);
    try {
      await request(`/experiments/${experimentId}/run`, { method: "POST" });
      setMessage("Optimization is running in the background.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to start.");
    } finally {
      setBusy(false);
    }
  }

  async function approve() {
    if (!best) return;
    setBusy(true);
    try {
      await request(`/candidates/${best.id}/approve`, {
        method: "POST",
        body: JSON.stringify({ reviewer_id: reviewer, comment }),
      });
      setMessage("Strategy approved and recorded in the review log.");
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to approve.");
      setBusy(false);
    }
  }

  return (
    <main>
      <header className="topbar">
        <div className="brandMark">T</div>
        <div>
          <p className="eyebrow">TEST GENERATION LAB</p>
          <h1>Prompt optimization, measured in execution.</h1>
        </div>
        <div className={`statusPill status-${experiment?.status ?? "idle"}`}>
          <span />
          {experiment?.status ?? "NO RUN"}
        </div>
      </header>

      <section className="hero">
        <div>
          <p className="kicker">COVERUP BASELINE × GEPA OPTIMIZATION</p>
          <h2>Compare one baseline with one optimized strategy.</h2>
          <p className="heroCopy">
            Run the fixed CoverUp prompt bundle, compare it with the GEPA-optimized
            bundle, and approve only a strategy supported by execution evidence.
          </p>
        </div>
        <div className="heroStats" aria-label="Experiment summary">
          <div><strong>{candidates.length}</strong><span>Strategies</span></div>
          <div><strong>{best ? percent(best.fitness_score) : "—"}</strong><span>Best score</span></div>
          <div><strong>{best ? percent(best.branch_coverage) : "—"}</strong><span>Best branch</span></div>
        </div>
      </section>

      <div className="workspace">
        <section className="panel createPanel">
          <div className="panelHeading">
            <span>01</span>
            <div><p>SETUP</p><h3>Create experiment</h3></div>
          </div>
          <form onSubmit={createExperiment}>
            <label>
              Experiment name
              <input
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                required
              />
            </label>
            <label>
              CoverUp baseline prompt file
              <input value={form.baseline_prompt} readOnly required />
            </label>
            <div className="fieldGrid">
              <label>
                Module path
                <input
                  value={form.module_path}
                  onChange={(event) =>
                    setForm({ ...form, module_path: event.target.value })
                  }
                  required
                />
              </label>
              <label>
                GEPA metric-call budget
                <input value="300" readOnly />
              </label>
            </div>
            <details>
              <summary>Dataset configuration</summary>
              <label>
                Dataset path
                <input
                  value={form.dataset_path}
                  onChange={(event) =>
                    setForm({ ...form, dataset_path: event.target.value })
                  }
                />
              </label>
              <label>
                Source root
                <input
                  value={form.source_root}
                  onChange={(event) =>
                    setForm({ ...form, source_root: event.target.value })
                  }
                />
              </label>
            </details>
            <button className="primary" disabled={busy} type="submit">
              Create experiment
            </button>
          </form>
        </section>

        <section className="panel runPanel">
          <div className="panelHeading">
            <span>02</span>
            <div><p>OPTIMIZE</p><h3>Run workspace</h3></div>
          </div>
          <div className="runControls">
            <input
              aria-label="Experiment ID"
              placeholder="Experiment ID"
              value={experimentId}
              onChange={(event) => setExperimentId(event.target.value)}
            />
            <button disabled={!experimentId || busy} onClick={runOptimization}>
              Start
            </button>
            <button disabled={!experimentId || busy} onClick={refresh}>
              Refresh
            </button>
          </div>
          <div className="console" role="status">
            <span>&gt;</span> {message}
          </div>

          <div className="paretoHeading">
            <div><p>STRATEGY COMPARISON</p><h4>CoverUp baseline vs. GEPA</h4></div>
            <span>{candidates.length}/2 strategies</span>
          </div>
          <div className="strategyComparison" aria-label="CoverUp and GEPA comparison">
            {candidates.map((candidate) => (
              <article
                className={candidate.id === best?.id ? "strategyCard best" : "strategyCard"}
                key={candidate.id}
              >
                <strong>{strategyName(candidate)}</strong>
                <span>Score {percent(candidate.fitness_score)}</span>
                <span>Statements {percent(candidate.statement_coverage)}</span>
                <span>Branches {percent(candidate.branch_coverage)}</span>
                <span>Valid targets {percent(candidate.pass_rate)}</span>
              </article>
            ))}
            {!candidates.length && (
              <p className="emptyChart">The two strategy measurements appear here.</p>
            )}
          </div>
        </section>
      </div>

      <section className="panel reviewPanel">
        <div className="panelHeading">
          <span>03</span>
          <div><p>HUMAN GATE</p><h3>Review strongest strategy</h3></div>
        </div>
        {best ? (
          <div className="reviewGrid">
            <div className="metricRail">
              {[
                ["Fitness", best.fitness_score],
                ["Valid targets", best.pass_rate],
                ["Statements", best.statement_coverage],
                ["Branches", best.branch_coverage],
              ].map(([label, value]) => (
                <div key={String(label)}>
                  <span>{label}</span>
                  <strong>{percent(Number(value))}</strong>
                  {baseline && best.id !== baseline.id && label !== "Fitness" && (
                    <small>
                      {signedPercent(
                        Number(value) -
                          Number(
                            label === "Valid targets"
                              ? baseline.pass_rate
                              : label === "Statements"
                                ? baseline.statement_coverage
                                : baseline.branch_coverage,
                          ),
                      )}{" "}
                      vs baseline
                    </small>
                  )}
                </div>
              ))}
            </div>
            <div>
              <h4>{strategyName(best)}</h4>
              <pre>{best.prompt_text}</pre>
            </div>
            <div className="approval">
              <div
                className={`regressionAudit ${
                  regressionMetrics.length ? "hasRegression" : ""
                }`}
              >
                <strong>Regression audit</strong>
                {best.id === baseline?.id ? (
                  <p>Only the baseline is available; no candidate comparison yet.</p>
                ) : regressionMetrics.length ? (
                  <ul>
                    {regressionMetrics.map(([label, delta]) => (
                      <li key={String(label)}>
                        {label}: {signedPercent(Number(delta))}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>No measured metric regressed against generation 0.</p>
                )}
              </div>
              <label>
                Reviewer
                <input value={reviewer} onChange={(event) => setReviewer(event.target.value)} />
              </label>
              <label>
                Decision note
                <textarea rows={4} value={comment} onChange={(event) => setComment(event.target.value)} />
              </label>
              <button className="approve" disabled={busy || best.status === "APPROVED"} onClick={approve}>
                {best.status === "APPROVED" ? "Approved" : "Approve strategy"}
              </button>
              <p>Approval is always explicit; no candidate deploys itself.</p>
            </div>
          </div>
        ) : (
          <div className="emptyState">
            <strong>No strategy selected.</strong>
            <span>Run an experiment and refresh the workspace to begin review.</span>
          </div>
        )}
      </section>

      <footer>
        <span>TESTGEN OPTIMIZATION SYSTEM</span>
        <span>Execution-grounded · Human-approved</span>
      </footer>
    </main>
  );
}
