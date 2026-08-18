import { ArrowLeft, ArrowRight, Check, FlaskConical } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useLocation } from "wouter";

import { useRepositories } from "@/app/providers";
import { Field, PageHeader, StatusBadge } from "@/components/PlatformUI";
import type { PromptRegistryEntry } from "@/domain/experiments";
import type { PythonProject } from "@/domain/projects";

const steps = ["Environments", "Setting", "Review"] as const;
const functionMethods = [
  ["random", "Select randomly"],
  ["most_branches", "Most branches"],
  ["most_statements", "Most statements"],
  ["manual", "Manual selection"],
] as const;
const models = [
  "vertex_ai/gemini-3.5-flash-lite",
  "vertex_ai/gemini-3.5-flash",
  "vertex_ai/gemini-2.5-flash",
  "openai/gpt-5-mini",
  "deepseek/deepseek-v4-flash",
];

function projectEnvironment(project: PythonProject) {
  return project.runtimeEnvironmentId ?? "unassigned";
}

function projectEnvironmentName(project: PythonProject) {
  return project.runtimeEnvironmentName ?? "Environment not named";
}

function environmentLabel(project: PythonProject) {
  return `${projectEnvironmentName(project)} · ${projectEnvironment(project)}`;
}

function PromptOption({ entry }: { entry: PromptRegistryEntry }) {
  return (
    <option value={entry.experimentId}>
      {entry.experimentName} · {entry.experimentId.slice(0, 8)}
    </option>
  );
}

export default function CreateTestSuite() {
  const [, navigate] = useLocation();
  const { promptRegistry, projects } = useRepositories();
  const [step, setStep] = useState(0);
  const [experimentId, setExperimentId] = useState("");
  const [promptRole, setPromptRole] = useState<"baseline" | "optimized">("optimized");
  const [environmentId, setEnvironmentId] = useState("");
  const [projectIds, setProjectIds] = useState<string[]>([]);
  const [method, setMethod] = useState<(typeof functionMethods)[number][0]>("random");
  const [functionCount, setFunctionCount] = useState(20);
  const [seed, setSeed] = useState(7);
  const [model, setModel] = useState(models[0]);
  const [created, setCreated] = useState(false);
  const promptsQuery = useQuery({
    queryKey: ["prompt-registry", "create-test-suite"],
    queryFn: ({ signal }) => promptRegistry.list(signal),
  });
  const projectsQuery = useQuery({
    queryKey: ["projects", "create-test-suite"],
    queryFn: async ({ signal }) => {
      const [samples, uploaded] = await Promise.all([
        projects.listSamples(signal),
        projects.list(signal),
      ]);
      return [
        ...samples,
        ...uploaded.filter((project) => !samples.some((sample) => sample.id === project.id)),
      ];
    },
  });
  const promptEntries = promptsQuery.data?.items ?? [];
  const projectEntries = useMemo(() => projectsQuery.data ?? [], [projectsQuery.data]);
  const selectedEntry = promptEntries.find((entry) => entry.experimentId === experimentId);
  const environments = useMemo(() => {
    const map = new Map<string, PythonProject>();
    for (const project of projectEntries) {
      const id = projectEnvironment(project);
      if (!map.has(id)) map.set(id, project);
    }
    return [...map.entries()];
  }, [projectEntries]);
  const environmentProjects = projectEntries.filter(
    (project) => projectEnvironment(project) === environmentId,
  );
  const selectedProjects = environmentProjects.filter((project) => projectIds.includes(project.id));
  const canContinue =
    (step === 0 && experimentId !== "" && environmentId !== "" && projectIds.length > 0) ||
    (step === 1 && functionCount >= 1 && model !== "") ||
    step === 2;

  const toggleProject = (projectId: string) => {
    setProjectIds((current) =>
      current.includes(projectId)
        ? current.filter((id) => id !== projectId)
        : [...current, projectId],
    );
  };

  const changeEnvironment = (value: string) => {
    setEnvironmentId(value);
    setProjectIds([]);
  };

  return (
    <div className="platform-page create-test-suite-page">
      <button className="back-link" onClick={() => navigate("/test-cases")}>
        <ArrowLeft size={15} /> Test Suites
      </button>
      <PageHeader
        eyebrow="Independent test generation"
        title="Create Test Suites"
        description="Generate a standalone suite from a prompt saved in Prompt Registry."
      />

      <div className="wizard-stepper" aria-label="Test suite creation steps">
        {steps.map((label, index) => (
          <div className={`wizard-step ${step === index ? "is-active" : ""}`} key={label}>
            <span>{index + 1}</span>
            <strong>{label}</strong>
          </div>
        ))}
      </div>

      {created && (
        <section className="platform-callout" role="status">
          <Check size={18} />
          <span>
            Test suite configuration saved locally. Backend generation will be connected next.
          </span>
        </section>
      )}

      {step === 0 && (
        <section className="platform-card wizard-panel">
          <div className="wizard-heading">
            <span className="eyebrow">Step 1</span>
            <h2>Environments</h2>
            <p>Choose a saved experiment prompt, a shared runtime environment, and its projects.</p>
          </div>
          <div className="platform-two-column create-suite-fields">
            <Field label="Experiment">
              <select
                value={experimentId}
                onChange={(event) => setExperimentId(event.target.value)}
              >
                <option value="">Select an experiment</option>
                {promptEntries.map((entry) => (
                  <PromptOption key={entry.experimentId} entry={entry} />
                ))}
              </select>
            </Field>
            <Field label="Prompt">
              <select
                value={promptRole}
                onChange={(event) => setPromptRole(event.target.value as typeof promptRole)}
              >
                <option value="baseline">Baseline prompt</option>
                <option value="optimized" disabled={!selectedEntry?.optimized}>
                  Final Prompt
                </option>
              </select>
            </Field>
          </div>
          <Field label="Environment" hint="Projects must use the same runtime environment.">
            <select
              value={environmentId}
              onChange={(event) => changeEnvironment(event.target.value)}
            >
              <option value="">Select an environment</option>
              {environments.map(([id, project]) => (
                <option key={id} value={id}>
                  {environmentLabel(project)}
                </option>
              ))}
            </select>
          </Field>
          <div className="create-suite-project-picker">
            <div className="card-heading">
              <div>
                <h3>Projects</h3>
                <p>{selectedProjects.length} selected</p>
              </div>
              <StatusBadge tone={environmentId ? "success" : "neutral"}>
                {environmentProjects.length} available
              </StatusBadge>
            </div>
            <div className="create-suite-project-list">
              {environmentProjects.map((project) => (
                <label
                  className={`create-suite-project ${projectIds.includes(project.id) ? "is-selected" : ""}`}
                  key={project.id}
                >
                  <input
                    type="checkbox"
                    checked={projectIds.includes(project.id)}
                    onChange={() => toggleProject(project.id)}
                  />
                  <span>
                    <strong>{project.name}</strong>
                    <small>
                      {project.functions} functions · {project.files} files
                    </small>
                  </span>
                </label>
              ))}
              {!environmentId && (
                <p className="muted-cell">Select an environment to view compatible projects.</p>
              )}
            </div>
          </div>
        </section>
      )}

      {step === 1 && (
        <section className="platform-card wizard-panel">
          <div className="wizard-heading">
            <span className="eyebrow">Step 2</span>
            <h2>Setting</h2>
            <p>Choose how functions are selected and which model generates the suite.</p>
          </div>
          <Field label="Select functions">
            <select
              value={method}
              onChange={(event) => setMethod(event.target.value as typeof method)}
            >
              {functionMethods.map(([value, label]) => (
                <option value={value} key={value}>
                  {label}
                </option>
              ))}
            </select>
          </Field>
          <div className="platform-two-column create-suite-fields">
            <Field label="Number of functions">
              <input
                type="number"
                min={1}
                value={functionCount}
                onChange={(event) => setFunctionCount(Number(event.target.value))}
              />
            </Field>
            <Field
              label="Random seed"
              hint={method === "random" ? "Used to make selection reproducible." : "None Available"}
            >
              <input
                type="number"
                min={0}
                value={method === "random" ? seed : ""}
                disabled={method !== "random"}
                placeholder={method === "random" ? undefined : "None Available"}
                onChange={(event) => setSeed(Number(event.target.value))}
              />
            </Field>
          </div>
          <Field label="Model">
            <select value={model} onChange={(event) => setModel(event.target.value)}>
              {models.map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </Field>
        </section>
      )}

      {step === 2 && (
        <section className="platform-card wizard-panel">
          <div className="wizard-heading">
            <span className="eyebrow">Step 3</span>
            <h2>Review</h2>
            <p>Confirm the standalone test suite configuration before creating it.</p>
          </div>
          <dl className="definition-list create-suite-review">
            <div>
              <dt>Experiment</dt>
              <dd>{selectedEntry?.experimentName ?? "Not selected"}</dd>
            </div>
            <div>
              <dt>Prompt</dt>
              <dd>{promptRole === "baseline" ? "Baseline prompt" : "Final Prompt"}</dd>
            </div>
            <div>
              <dt>Environment</dt>
              <dd>
                {environmentProjects[0] ? environmentLabel(environmentProjects[0]) : "Not selected"}
              </dd>
            </div>
            <div>
              <dt>Projects</dt>
              <dd>
                {selectedProjects.map((project) => project.name).join(", ") || "Not selected"}
              </dd>
            </div>
            <div>
              <dt>Function selection</dt>
              <dd>
                {functionMethods.find(([value]) => value === method)?.[1]} · {functionCount}{" "}
                functions
              </dd>
            </div>
            <div>
              <dt>Seed</dt>
              <dd>{method === "random" ? seed : "None Available"}</dd>
            </div>
            <div>
              <dt>Model</dt>
              <dd>{model}</dd>
            </div>
          </dl>
        </section>
      )}

      <div className="wizard-actions">
        <button
          className="secondary-button"
          type="button"
          onClick={() => (step === 0 ? navigate("/test-cases") : setStep(step - 1))}
        >
          <ArrowLeft size={15} /> {step === 0 ? "Cancel" : "Back"}
        </button>
        {step < 2 ? (
          <button
            className="primary-button"
            type="button"
            disabled={!canContinue}
            onClick={() => setStep(step + 1)}
          >
            Continue <ArrowRight size={15} />
          </button>
        ) : (
          <button
            className="primary-button"
            type="button"
            disabled={!canContinue}
            onClick={() => setCreated(true)}
          >
            <FlaskConical size={15} /> Create Test Suites
          </button>
        )}
      </div>
    </div>
  );
}
