import { useMemo, useState } from "react";
import { useLocation } from "wouter";

import { Field, PageHeader, StatusBadge } from "@/components/PlatformUI";
import { projectFunctions, pythonProjects } from "@/mocks/fixtures/platform";

const steps = ["Projects", "Functions", "Dataset", "Optimization", "Review", "Run"];
const methods = [
  {
    id: "random",
    title: "Random",
    description: "Shuffle all eligible functions with a reproducible seed.",
  },
  {
    id: "branch",
    title: "Highest branch count",
    description: "Select top N by branches, then shuffle before splitting.",
  },
  {
    id: "statement",
    title: "Highest statement count",
    description: "Select top N by statements, then shuffle before splitting.",
  },
  {
    id: "manual",
    title: "Manual selection",
    description: "Assign individual functions to train, validation or test.",
  },
];

export default function CreateExperiment() {
  const [, navigate] = useLocation();
  const [step, setStep] = useState(0);
  const [selectedProjects, setSelectedProjects] = useState(["isort", "attrs"]);
  const [method, setMethod] = useState("branch");
  const [limits, setLimits] = useState({ train: 60, validation: 20, test: 20 });
  const [seed, setSeed] = useState(839201);
  const [assignments, setAssignments] = useState<Record<string, string>>({
    "fn-1": "train",
    "fn-2": "test",
    "fn-3": "validation",
  });
  const available = useMemo(
    () =>
      pythonProjects
        .filter((project) => selectedProjects.includes(project.id))
        .reduce((sum, project) => sum + project.functions, 0),
    [selectedProjects],
  );
  const requested = limits.train + limits.validation + limits.test;
  const limitsValid =
    Number.isInteger(limits.train) &&
    Number.isInteger(limits.validation) &&
    Number.isInteger(limits.test) &&
    limits.train >= 0 &&
    limits.validation >= 0 &&
    limits.test > 0 &&
    requested <= available;

  const toggleProject = (id: string) =>
    setSelectedProjects((current) =>
      current.includes(id) ? current.filter((projectId) => projectId !== id) : [...current, id],
    );
  const canContinue = (step !== 0 || selectedProjects.length > 0) && (step !== 2 || limitsValid);

  return (
    <div className="platform-page wizard-page">
      <button className="back-link" onClick={() => navigate("/experiments")}>
        ← All experiments
      </button>
      <PageHeader
        eyebrow="New experiment"
        title="Build a reproducible evaluation"
        description="Select code, create an isolated dataset and configure prompt optimization."
        actions={<button className="secondary-button">Save draft</button>}
      />
      <ol className="wizard-steps">
        {steps.map((item, index) => (
          <li key={item} className={index === step ? "active" : index < step ? "complete" : ""}>
            <span>{index < step ? "✓" : index + 1}</span>
            <b>{item}</b>
          </li>
        ))}
      </ol>

      <div className="wizard-shell">
        <section className="wizard-content">
          {step === 0 && <ProjectStep selected={selectedProjects} onToggle={toggleProject} />}
          {step === 1 && <FunctionsStep projectIds={selectedProjects} />}
          {step === 2 && (
            <DatasetStep
              method={method}
              setMethod={setMethod}
              limits={limits}
              setLimits={setLimits}
              seed={seed}
              setSeed={setSeed}
              available={available}
              assignments={assignments}
              setAssignments={setAssignments}
            />
          )}
          {step === 3 && <OptimizationStep />}
          {step === 4 && (
            <ReviewStep
              selectedProjects={selectedProjects}
              method={method}
              limits={limits}
              seed={seed}
            />
          )}
          {step === 5 && <RunStep />}
        </section>

        {step < 5 && (
          <aside className="wizard-summary">
            <span className="eyebrow">Experiment draft</span>
            <h3>GEPA coverage benchmark</h3>
            <dl>
              <div>
                <dt>Projects</dt>
                <dd>{selectedProjects.length}</dd>
              </div>
              <div>
                <dt>Available functions</dt>
                <dd>{available}</dd>
              </div>
              <div>
                <dt>Requested dataset</dt>
                <dd>{requested}</dd>
              </div>
              <div>
                <dt>Sampling</dt>
                <dd>{methods.find((item) => item.id === method)?.title}</dd>
              </div>
              <div>
                <dt>Model</dt>
                <dd>Gemini 2.5 Pro</dd>
              </div>
            </dl>
            <div className={limitsValid ? "summary-valid" : "summary-invalid"}>
              {limitsValid
                ? "✓ Configuration is valid"
                : limits.test <= 0
                  ? "Test set must contain at least one function"
                  : requested > available
                    ? `Need ${requested - available} more functions`
                    : "Dataset limits must be non-negative integers"}
            </div>
          </aside>
        )}
      </div>

      <div className="wizard-actions">
        <button
          className="secondary-button"
          disabled={step === 0}
          onClick={() => setStep((value) => Math.max(0, value - 1))}
        >
          Back
        </button>
        <span>
          Step {step + 1} of {steps.length}
        </span>
        {step < 4 && (
          <button
            className="primary-button"
            disabled={!canContinue}
            onClick={() => setStep((value) => value + 1)}
          >
            Continue →
          </button>
        )}
        {step === 4 && (
          <button className="primary-button" onClick={() => setStep(5)}>
            Confirm and start
          </button>
        )}
        {step === 5 && (
          <button className="primary-button" onClick={() => navigate("/runs/EXP-2409")}>
            Open experiment
          </button>
        )}
      </div>
    </div>
  );
}

function ProjectStep({
  selected,
  onToggle,
}: {
  selected: string[];
  onToggle: (id: string) => void;
}) {
  return (
    <>
      <div className="wizard-heading">
        <span className="eyebrow">Step 1</span>
        <h2>Select Python projects</h2>
        <p>Choose one or more validated project versions for this experiment.</p>
      </div>
      <div className="select-project-grid">
        {pythonProjects.map((project) => {
          const active = selected.includes(project.id);
          return (
            <button
              key={project.id}
              className={active ? "select-project-card selected" : "select-project-card"}
              onClick={() => onToggle(project.id)}
            >
              <span className="project-checkbox">{active ? "✓" : ""}</span>
              <div>
                <h3>{project.name}</h3>
                <p>{project.description}</p>
              </div>
              <StatusBadge tone={project.status === "ready" ? "success" : "warning"}>
                {project.status === "ready" ? "Ready" : "Warning"}
              </StatusBadge>
              <dl>
                <div>
                  <dt>Version</dt>
                  <dd>{project.commit}</dd>
                </div>
                <div>
                  <dt>Python</dt>
                  <dd>{project.python}</dd>
                </div>
                <div>
                  <dt>Files</dt>
                  <dd>{project.files}</dd>
                </div>
                <div>
                  <dt>Functions</dt>
                  <dd>{project.functions}</dd>
                </div>
              </dl>
              <span className="card-link">View project settings →</span>
            </button>
          );
        })}
      </div>
      <div className="selection-footer">
        <strong>
          {selected.length} project{selected.length === 1 ? "" : "s"} selected
        </strong>
        <span>
          {pythonProjects
            .filter((item) => selected.includes(item.id))
            .reduce((sum, item) => sum + item.functions, 0)}{" "}
          functions available
        </span>
      </div>
    </>
  );
}

function FunctionsStep({ projectIds }: { projectIds: string[] }) {
  const rows = projectFunctions.filter((item) => projectIds.includes(item.project));
  return (
    <>
      <div className="wizard-heading">
        <span className="eyebrow">Step 2</span>
        <h2>Review analyzed functions</h2>
        <p>AST extraction is complete. Coverage metadata is mapped to each function range.</p>
      </div>
      <div className="analysis-progress">
        <div>
          <span className="validation-check">✓</span>
          <div>
            <strong>Analysis completed</strong>
            <p>
              {projectIds.length} projects · 73 files · {rows.length} preview rows
            </p>
          </div>
        </div>
        <StatusBadge tone="success">Cached snapshot</StatusBadge>
      </div>
      <div className="toolbar-controls function-filters">
        <input placeholder="Search function or file…" />
        <select>
          <option>All projects</option>
          {projectIds.map((id) => (
            <option key={id}>{id}</option>
          ))}
        </select>
        <select>
          <option>All statuses</option>
          <option>Valid only</option>
        </select>
      </div>
      <div className="table-scroll">
        <table className="platform-table">
          <thead>
            <tr>
              <th>Project</th>
              <th>File / class</th>
              <th>Function</th>
              <th>Lines</th>
              <th>Statements</th>
              <th>Branches</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((item) => (
              <tr key={item.id}>
                <td>{item.project}</td>
                <td>
                  <strong>{item.file}</strong>
                  <small>{item.className || "Module"}</small>
                </td>
                <td>
                  <code>{item.name}</code>
                </td>
                <td>{item.lines}</td>
                <td>{item.statements}</td>
                <td>{item.branches}</td>
                <td>
                  <StatusBadge tone={item.status === "Valid" ? "success" : "warning"}>
                    {item.status}
                  </StatusBadge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function DatasetStep({
  method,
  setMethod,
  limits,
  setLimits,
  seed,
  setSeed,
  available,
  assignments,
  setAssignments,
}: {
  method: string;
  setMethod: (value: string) => void;
  limits: { train: number; validation: number; test: number };
  setLimits: (value: { train: number; validation: number; test: number }) => void;
  seed: number;
  setSeed: (value: number) => void;
  available: number;
  assignments: Record<string, string>;
  setAssignments: (value: Record<string, string>) => void;
}) {
  const total = limits.train + limits.validation + limits.test;
  return (
    <>
      <div className="wizard-heading">
        <span className="eyebrow">Step 3</span>
        <h2>Configure dataset</h2>
        <p>Build mutually exclusive train, validation and test sets.</p>
      </div>
      <div className="limit-grid">
        {(["train", "validation", "test"] as const).map((key) => (
          <Field key={key} label={`${key[0].toUpperCase() + key.slice(1)} limit`}>
            <input
              type="number"
              min={key === "test" ? 1 : 0}
              value={limits[key]}
              onChange={(event) => setLimits({ ...limits, [key]: Number(event.target.value) })}
            />
          </Field>
        ))}
        <div className="limit-total">
          <span>Requested</span>
          <strong>
            {total} / {available}
          </strong>
          <small>{available - total} functions remaining</small>
        </div>
      </div>
      <div className="split-bar">
        <span style={{ width: `${(limits.train / total) * 100}%` }}>Train {limits.train}</span>
        <span style={{ width: `${(limits.validation / total) * 100}%` }}>
          Val {limits.validation}
        </span>
        <span style={{ width: `${(limits.test / total) * 100}%` }}>Test {limits.test}</span>
      </div>
      <h3 className="section-label">Sampling method</h3>
      <div className="method-grid">
        {methods.map((item) => (
          <button
            key={item.id}
            className={method === item.id ? "method-card active" : "method-card"}
            onClick={() => setMethod(item.id)}
          >
            <span className="radio-dot" />
            <strong>{item.title}</strong>
            <p>{item.description}</p>
          </button>
        ))}
      </div>
      <div className="seed-row">
        <Field label="Random seed" hint="Same inputs and seed reproduce the exact split">
          <input
            type="number"
            value={seed}
            onChange={(event) => setSeed(Number(event.target.value))}
          />
        </Field>
        <button
          className="secondary-button"
          onClick={() => setSeed(420000 + Math.floor(Math.random() * 9999))}
        >
          Generate seed
        </button>
      </div>
      {method === "manual" && (
        <div className="manual-panel">
          <div className="card-heading">
            <div>
              <h2>Manual assignment</h2>
              <p>Each function can belong to exactly one set.</p>
            </div>
            <StatusBadge tone="info">3 assigned</StatusBadge>
          </div>
          {projectFunctions.slice(0, 4).map((item) => (
            <div className="manual-row" key={item.id}>
              <div>
                <strong>{item.name}</strong>
                <span>
                  {item.project} · {item.file}
                </span>
              </div>
              <span>{item.branches} branches</span>
              <select
                value={assignments[item.id] ?? "unassigned"}
                onChange={(event) =>
                  setAssignments({ ...assignments, [item.id]: event.target.value })
                }
              >
                <option value="unassigned">Unassigned</option>
                <option value="train">Train</option>
                <option value="validation">Validation</option>
                <option value="test">Test</option>
              </select>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

function OptimizationStep() {
  return (
    <>
      <div className="wizard-heading">
        <span className="eyebrow">Step 4</span>
        <h2>Prompt and optimization</h2>
        <p>These values are snapshotted with the experiment for reproducibility.</p>
      </div>
      <div className="configuration-grid">
        <section className="config-section">
          <h3>Prompt & model</h3>
          <Field label="Baseline prompt">
            <select>
              <option>Unit Test Generator · v3</option>
              <option>Coverage First · v2</option>
            </select>
          </Field>
          <Field label="Gemini model">
            <select>
              <option>Gemini 2.5 Pro</option>
              <option>Gemini 2.5 Flash</option>
            </select>
          </Field>
          <div className="form-grid">
            <Field label="Temperature">
              <input defaultValue="0.3" />
            </Field>
            <Field label="Max output tokens">
              <input defaultValue="4096" />
            </Field>
          </div>
        </section>
        <section className="config-section">
          <h3>Optimization strategy</h3>
          <Field label="Optimizer">
            <select>
              <option>GEPA</option>
              <option>DSPy MIPROv2</option>
              <option>Custom evolutionary</option>
            </select>
          </Field>
          <div className="form-grid">
            <Field label="Iterations">
              <input defaultValue="10" />
            </Field>
            <Field label="Candidates / iteration">
              <input defaultValue="4" />
            </Field>
            <Field label="Cost budget">
              <input defaultValue="$12.00" />
            </Field>
            <Field label="Stop patience">
              <input defaultValue="3 iterations" />
            </Field>
          </div>
        </section>
        <section className="config-section score-config">
          <h3>Scoring formula</h3>
          <div className="weight-row">
            <span>Branch coverage</span>
            <input defaultValue="0.50" />
            <b>50%</b>
          </div>
          <div className="weight-row">
            <span>Statement coverage</span>
            <input defaultValue="0.30" />
            <b>30%</b>
          </div>
          <div className="weight-row">
            <span>Test pass rate</span>
            <input defaultValue="0.20" />
            <b>20%</b>
          </div>
          <div className="formula-preview">
            Score = 0.50 × Branch + 0.30 × Statement + 0.20 × Pass rate
          </div>
        </section>
        <section className="config-section">
          <h3>Execution</h3>
          <div className="form-grid">
            <Field label="Parallel workers">
              <input defaultValue="4" />
            </Field>
            <Field label="Function timeout">
              <input defaultValue="120 sec" />
            </Field>
            <Field label="Retry failed">
              <input defaultValue="1" />
            </Field>
            <Field label="Network">
              <select>
                <option>Disabled</option>
              </select>
            </Field>
          </div>
        </section>
      </div>
    </>
  );
}

function ReviewStep({
  selectedProjects,
  method,
  limits,
  seed,
}: {
  selectedProjects: string[];
  method: string;
  limits: { train: number; validation: number; test: number };
  seed: number;
}) {
  return (
    <>
      <div className="wizard-heading">
        <span className="eyebrow">Step 5</span>
        <h2>Review and confirm</h2>
        <p>Check the immutable snapshot before allocating execution resources.</p>
      </div>
      <div className="review-grid">
        <section className="review-section">
          <h3>Scope</h3>
          <dl className="definition-list">
            <div>
              <dt>Projects</dt>
              <dd>{selectedProjects.join(", ")}</dd>
            </div>
            <div>
              <dt>Versions</dt>
              <dd>9262aa8 · bd8f611</dd>
            </div>
            <div>
              <dt>Dataset</dt>
              <dd>
                {limits.train} / {limits.validation} / {limits.test}
              </dd>
            </div>
            <div>
              <dt>Sampling</dt>
              <dd>{methods.find((item) => item.id === method)?.title}</dd>
            </div>
            <div>
              <dt>Seed</dt>
              <dd>{seed}</dd>
            </div>
          </dl>
        </section>
        <section className="review-section">
          <h3>Optimization</h3>
          <dl className="definition-list">
            <div>
              <dt>Prompt</dt>
              <dd>Unit Test Generator v3</dd>
            </div>
            <div>
              <dt>Model</dt>
              <dd>Gemini 2.5 Pro</dd>
            </div>
            <div>
              <dt>Optimizer</dt>
              <dd>GEPA · 10 iterations</dd>
            </div>
            <div>
              <dt>Budget</dt>
              <dd>$12.00</dd>
            </div>
            <div>
              <dt>Score priority</dt>
              <dd>50% branch coverage</dd>
            </div>
          </dl>
        </section>
      </div>
      <section className="validation-box">
        <h3>Dataset and runtime validation</h3>
        {[
          "No duplicate functions across splits",
          "Test set is isolated from optimization",
          "Project commits and settings are recorded",
          "Random seed is stored",
          "Runtime and dependencies are valid",
          "Scoring weights total 100%",
        ].map((item) => (
          <div key={item}>
            <span>✓</span>
            {item}
          </div>
        ))}
      </section>
    </>
  );
}

function RunStep() {
  const phases = [
    { name: "Preparing environment", status: "Completed", detail: "Images and dependencies ready" },
    { name: "Running baseline", status: "Completed", detail: "100 functions evaluated" },
    { name: "Optimizing prompt", status: "Running", detail: "Candidate 18 · iteration 6/10" },
    { name: "Selecting best prompt", status: "Pending", detail: "Waiting for validation" },
    { name: "Evaluating test set", status: "Pending", detail: "20 isolated functions" },
    { name: "Aggregating results", status: "Pending", detail: "Coverage and score" },
  ];
  return (
    <>
      <div className="wizard-heading">
        <span className="eyebrow">EXP-2409 · Running</span>
        <h2>Experiment in progress</h2>
        <p>The run continues safely if you leave this page.</p>
      </div>
      <div className="run-overview">
        <div className="progress-ring">
          <strong>64%</strong>
          <span>overall</span>
        </div>
        <div>
          <h3>GEPA coverage benchmark</h3>
          <p>64 of 100 function evaluations completed · 08:42 elapsed</p>
          <div className="run-stats">
            <span>
              <b>58</b> passed
            </span>
            <span>
              <b>4</b> failed
            </span>
            <span>
              <b>2</b> timeout
            </span>
            <span>
              <b>0</b> coverage errors
            </span>
          </div>
        </div>
      </div>
      <div className="phase-list">
        {phases.map((phase, index) => (
          <div className={`phase-row phase-${phase.status.toLowerCase()}`} key={phase.name}>
            <span>{phase.status === "Completed" ? "✓" : index + 1}</span>
            <div>
              <strong>{phase.name}</strong>
              <small>{phase.detail}</small>
            </div>
            <StatusBadge
              tone={
                phase.status === "Completed"
                  ? "success"
                  : phase.status === "Running"
                    ? "info"
                    : "neutral"
              }
            >
              {phase.status}
            </StatusBadge>
          </div>
        ))}
      </div>
      <div className="log-panel">
        <div>
          <span>[15:41:22]</span> Running isort.api.sort_code_string
        </div>
        <div>
          <span>[15:41:25]</span> Branch coverage improved to 76.8%
        </div>
        <div>
          <span>[15:41:26]</span> Candidate prompt V4 selected for next iteration
        </div>
      </div>
    </>
  );
}
