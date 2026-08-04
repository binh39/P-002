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
  mutation_score: number;
  cost_usd: number;
  latency_seconds: number;
  status: string;
};

const initialForm = {
  name: "isort prompt optimization",
  baseline_prompt:
    "Generate focused, deterministic pytest tests for uncovered execution paths.",
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
      ["Pass rate", best.pass_rate - baseline.pass_rate],
      ["Statement coverage", best.statement_coverage - baseline.statement_coverage],
      ["Branch coverage", best.branch_coverage - baseline.branch_coverage],
      ["Mutation score", best.mutation_score - baseline.mutation_score],
    ].filter(([, delta]) => Number(delta) < 0);
  }, [best, baseline]);
  const maxCost = Math.max(0.01, ...candidates.map((item) => item.cost_usd));

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
      setMessage("Candidate approved and recorded in the review log.");
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
          <p className="kicker">GEPA × PYTEST × MUTATION TESTING</p>
          <h2>Move prompts from intuition to evidence.</h2>
          <p className="heroCopy">
            Create a controlled experiment, inspect the Pareto trade-off, and
            approve only candidates that survive runtime checks.
          </p>
        </div>
        <div className="heroStats" aria-label="Experiment summary">
          <div><strong>{candidates.length}</strong><span>Candidates</span></div>
          <div><strong>{best ? percent(best.mutation_score) : "—"}</strong><span>Best mutation</span></div>
          <div><strong>${best?.cost_usd.toFixed(3) ?? "—"}</strong><span>Best cost</span></div>
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
              Baseline prompt
              <textarea
                value={form.baseline_prompt}
                onChange={(event) =>
                  setForm({ ...form, baseline_prompt: event.target.value })
                }
                rows={5}
                required
              />
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
                Budget (USD)
                <input
                  type="number"
                  min="0.1"
                  step="0.1"
                  value={form.budget_limit}
                  onChange={(event) =>
                    setForm({ ...form, budget_limit: Number(event.target.value) })
                  }
                  required
                />
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
            <div><p>PARETO VIEW</p><h4>Mutation score vs. cost</h4></div>
            <span>{candidates.length} points</span>
          </div>
          <div className="chart" aria-label="Candidate Pareto scatter plot">
            <span className="axisY">MUTATION</span>
            <span className="axisX">COST →</span>
            {candidates.map((candidate) => (
              <button
                className={`plotPoint ${candidate.id === best?.id ? "best" : ""}`}
                key={candidate.id}
                style={{
                  left: `${8 + (candidate.cost_usd / maxCost) * 82}%`,
                  bottom: `${8 + candidate.mutation_score * 78}%`,
                }}
                title={`Gen ${candidate.generation}: ${percent(candidate.mutation_score)} mutation, $${candidate.cost_usd.toFixed(3)}`}
                aria-label={`Generation ${candidate.generation}, mutation ${percent(candidate.mutation_score)}, cost $${candidate.cost_usd.toFixed(3)}`}
              />
            ))}
            {!candidates.length && (
              <p className="emptyChart">Candidate measurements appear here.</p>
            )}
          </div>
        </section>
      </div>

      <section className="panel reviewPanel">
        <div className="panelHeading">
          <span>03</span>
          <div><p>HUMAN GATE</p><h3>Review strongest candidate</h3></div>
        </div>
        {best ? (
          <div className="reviewGrid">
            <div className="metricRail">
              {[
                ["Fitness", best.fitness_score],
                ["Pass rate", best.pass_rate],
                ["Statements", best.statement_coverage],
                ["Branches", best.branch_coverage],
                ["Mutation", best.mutation_score],
              ].map(([label, value]) => (
                <div key={String(label)}>
                  <span>{label}</span>
                  <strong>{percent(Number(value))}</strong>
                  {baseline && best.id !== baseline.id && label !== "Fitness" && (
                    <small>
                      {signedPercent(
                        Number(value) -
                          Number(
                            label === "Pass rate"
                              ? baseline.pass_rate
                              : label === "Statements"
                                ? baseline.statement_coverage
                                : label === "Branches"
                                  ? baseline.branch_coverage
                                  : baseline.mutation_score,
                          ),
                      )}{" "}
                      vs baseline
                    </small>
                  )}
                </div>
              ))}
            </div>
            <pre>{best.prompt_text}</pre>
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
                {best.status === "APPROVED" ? "Approved" : "Approve candidate"}
              </button>
              <p>Approval is always explicit; no candidate deploys itself.</p>
            </div>
          </div>
        ) : (
          <div className="emptyState">
            <strong>No candidate selected.</strong>
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
