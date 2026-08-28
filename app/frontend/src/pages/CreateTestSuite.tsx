import { useMutation, useQueries, useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, FlaskConical } from "lucide-react";
import { useMemo, useState } from "react";
import { useLocation, useSearch } from "wouter";

import { useRepositories } from "@/app/providers";
import { Field, PageHeader, StatusBadge } from "@/components/PlatformUI";
import {
  selectCandidateFunctions,
  type ExperimentFunction,
  type SamplingMethod,
} from "@/domain/experimentConfiguration";
import type { PromptRegistryEntry } from "@/domain/experiments";
import type { PythonProject } from "@/domain/projects";

const steps = ["Projects & runtimes", "Setting", "Review"] as const;
const functionMethods: Array<{ id: SamplingMethod; title: string; description: string }> = [
  { id: "random", title: "Random", description: "Shuffle valid functions with the saved seed." },
  {
    id: "most_branches",
    title: "Most branches",
    description: "Prioritize the most branch-heavy functions.",
  },
  {
    id: "most_statements",
    title: "Most statements",
    description: "Prioritize the most statement-heavy functions.",
  },
  {
    id: "manual",
    title: "Manual",
    description: "Choose exactly the functions to generate tests for.",
  },
];
const models = [
  "google/gemini-2.5-flash",
  "google/gemini-2.5-flash-lite",
  "google/gemini-2.5-pro",
  "vertex_ai/gemini-2.5-flash",
  "vertex_ai/gemini-2.5-flash-lite",
  "vertex_ai/gemini-2.5-pro",
  "vertex_ai/gemini-3.1-flash-lite",
  "vertex_ai/gemini-3.1-pro-preview",
  "vertex_ai/gemini-3.5-flash",
  "vertex_ai/gemini-3.5-flash-lite",
  "vertex_ai/gemini-3.6-flash",
  "openai/gpt-4.1-mini",
  "openai/gpt-4.1",
  "openai/gpt-5-mini",
  "openai/gpt-5",
  "deepseek/deepseek-v4-flash",
  "deepseek/deepseek-v4-pro",
] as const;

function projectEnvironment(project: PythonProject) {
  return project.runtimeEnvironmentId ?? "unassigned";
}

function environmentLabel(project: PythonProject) {
  return `${project.runtimeEnvironmentName || "Runtime environment"} · ${projectEnvironment(project)}`;
}

function functionKey(projectId: string, functionId: string) {
  return `${projectId}::${functionId}`;
}

function promptOption(entry: PromptRegistryEntry) {
  return `${entry.experimentName} · ${entry.experimentId.slice(0, 8)}`;
}

function newIdempotencyKey() {
  const suffix =
    globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `test-suite-${suffix}`;
}

export default function CreateTestSuite() {
  const [, navigate] = useLocation();
  const search = useSearch();
  const { promptRegistry, projects, testGeneration } = useRepositories();
  const defaults = useMemo(() => new URLSearchParams(search), [search]);
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [experimentId, setExperimentId] = useState(() => defaults.get("experiment") ?? "");
  const [promptRole, setPromptRole] = useState<"baseline" | "optimized">(
    defaults.get("prompt") === "baseline" ? "baseline" : "optimized",
  );
  const [environmentId, setEnvironmentId] = useState("");
  const [projectIds, setProjectIds] = useState<string[]>([]);
  const [method, setMethod] = useState<SamplingMethod>("random");
  const [functionCount, setFunctionCount] = useState(20);
  const [manualFunctionIds, setManualFunctionIds] = useState<string[]>([]);
  const [seed, setSeed] = useState(7);
  const [model, setModel] = useState<(typeof models)[number]>(models[0]);
  const [searchTerm, setSearchTerm] = useState("");

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
  const entries = promptsQuery.data?.items ?? [];
  const selectedEntry = entries.find((entry) => entry.experimentId === experimentId);
  const resolvedPromptRole =
    promptRole === "optimized" && !selectedEntry?.optimized ? "baseline" : promptRole;
  const allowedProjects = useMemo(
    () =>
      (projectsQuery.data ?? []).filter((project) =>
        selectedEntry?.projectIds.includes(project.id),
      ),
    [projectsQuery.data, selectedEntry?.projectIds],
  );
  const environments = useMemo(() => {
    const values = new Map<string, PythonProject>();
    for (const project of allowedProjects) values.set(projectEnvironment(project), project);
    return [...values.entries()];
  }, [allowedProjects]);
  // Every uploaded project owns its runtime. A suite may therefore combine
  // projects with different Python/dependency environments.
  const environmentProjects = allowedProjects;
  const selectedProjects = environmentProjects.filter((project) => projectIds.includes(project.id));
  const functionQueries = useQueries({
    queries: selectedProjects.map((project) => ({
      queryKey: ["projects", project.id, "functions", "create-test-suite"],
      queryFn: ({ signal }: { signal: AbortSignal }) => projects.listFunctions(project.id, signal),
      staleTime: 5 * 60_000,
    })),
  });
  const functions = useMemo<ExperimentFunction[]>(
    () =>
      functionQueries.flatMap((query, index) => {
        const project = selectedProjects[index];
        if (!project || !query.data) return [];
        return query.data.map((item) => ({
          ...item,
          key: functionKey(project.id, item.id),
          projectName: project.name,
        }));
      }),
    [functionQueries, selectedProjects],
  );
  const validFunctions = useMemo(
    () => functions.filter((item) => item.status === "Valid"),
    [functions],
  );
  const selectedFunctions = useMemo(() => {
    if (method === "manual")
      return validFunctions.filter((item) => manualFunctionIds.includes(item.key));
    return selectCandidateFunctions(
      validFunctions,
      method,
      Math.min(functionCount, validFunctions.length),
      seed,
    );
  }, [functionCount, manualFunctionIds, method, seed, validFunctions]);
  const functionsLoading = functionQueries.some((query) => query.isPending);
  const functionsError = functionQueries.find((query) => query.isError)?.error;
  const filteredFunctions = validFunctions.filter((item) =>
    `${item.projectName} ${item.file} ${item.className} ${item.name}`
      .toLowerCase()
      .includes(searchTerm.toLowerCase()),
  );

  const create = useMutation({
    mutationFn: () =>
      testGeneration.create(experimentId, {
        promptRole: resolvedPromptRole,
        name: name.trim(),
        projectIds,
        samplingMethod: method,
        functionCount: method === "manual" ? null : functionCount,
        functionIds: method === "manual" ? manualFunctionIds : [],
        model,
        randomSeed: seed,
        idempotencyKey: newIdempotencyKey(),
      }),
    onSuccess: (run) => navigate(`/test-cases/${run.id}`),
  });

  const environmentValid = Boolean(selectedEntry && projectIds.length);
  const selectionValid =
    !functionsLoading &&
    !functionsError &&
    (method === "manual"
      ? selectedFunctions.length > 0
      : Number.isInteger(functionCount) &&
        functionCount >= 1 &&
        functionCount <= validFunctions.length);
  const reviewValid = name.trim().length > 0;
  const canContinue = [environmentValid && reviewValid, selectionValid, true][step];

  const chooseExperiment = (value: string) => {
    setExperimentId(value);
    // The suite name describes the user's intended output, not the prompt source.
    // Keep it intact when they compare or switch Prompt Registry experiments.
  };
  const chooseEnvironment = (value: string) => {
    setEnvironmentId(value);
    setProjectIds([]);
  };
  const toggleProject = (projectId: string) => {
    setProjectIds((current) =>
      current.includes(projectId)
        ? current.filter((id) => id !== projectId)
        : [...current, projectId],
    );
    setManualFunctionIds([]);
  };
  const toggleFunction = (id: string) =>
    setManualFunctionIds((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    );

  if (promptsQuery.isError || projectsQuery.isError) {
    return (
      <PageError
        title="Test Suite setup is unavailable"
        error={promptsQuery.error ?? projectsQuery.error}
      />
    );
  }
  if (promptsQuery.isPending || projectsQuery.isPending) {
    return <PageState message="Loading saved prompts and projects…" />;
  }

  return (
    <div className="platform-page create-test-suite-page">
      <button className="back-link" onClick={() => navigate("/test-cases")}>
        <ArrowLeft size={15} /> Test Suites
      </button>
      <PageHeader
        eyebrow="Independent test generation"
        title="Create Test Suite"
        description="Generate an executable test suite from a saved Prompt Registry prompt."
      />
      <div className="wizard-stepper" aria-label="Test suite creation steps">
        {steps.map((label, index) => (
          <div className={`wizard-step ${step === index ? "is-active" : ""}`} key={label}>
            <span>{index + 1}</span>
            <strong>{label}</strong>
          </div>
        ))}
      </div>

      {step === 0 && (
        <section className="platform-card wizard-panel">
          <div className="wizard-heading">
            <span className="eyebrow">Step 1</span>
            <h2>Projects & runtimes</h2>
            <p>
              Select a prompt and the projects to test. Each project runs in its own prepared venv.
            </p>
          </div>
          <Field
            label="Test Suite name"
            hint="This name is displayed in Test Suites and does not change the saved prompt."
          >
            <input
              value={name}
              maxLength={120}
              placeholder="Example: isort final prompt regression suite"
              onChange={(event) => setName(event.target.value)}
            />
          </Field>
          <div className="platform-two-column create-suite-fields">
            <Field label="Experiment">
              <select
                value={experimentId}
                onChange={(event) => chooseExperiment(event.target.value)}
              >
                <option value="">Select an experiment</option>
                {entries.map((entry) => (
                  <option key={entry.experimentId} value={entry.experimentId}>
                    {promptOption(entry)}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Prompt">
              <select
                value={resolvedPromptRole}
                onChange={(event) => setPromptRole(event.target.value as typeof promptRole)}
              >
                <option value="baseline">Baseline prompt</option>
                <option value="optimized" disabled={!selectedEntry?.optimized}>
                  Final Prompt
                </option>
              </select>
            </Field>
          </div>
          <Field
            label="Runtime label"
            hint="Projects keep independent Python and dependency environments; grouping is optional."
          >
            <select
              value={environmentId}
              disabled={!selectedEntry}
              onChange={(event) => chooseEnvironment(event.target.value)}
            >
              <option value="">All project runtimes</option>
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
                <p className="muted-cell">
                  All project runtimes are available; choose a label to filter.
                </p>
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
            <p>
              Selection is applied by the backend to the immutable project snapshot before the job
              is queued.
            </p>
          </div>
          <div className="sampling-method-grid">
            {functionMethods.map((item) => (
              <button
                key={item.id}
                type="button"
                className={method === item.id ? "sampling-card selected" : "sampling-card"}
                onClick={() => setMethod(item.id)}
                aria-pressed={method === item.id}
              >
                <span className="radio-dot" />
                <strong>{item.title}</strong>
                <small>{item.description}</small>
              </button>
            ))}
          </div>
          {functionsLoading && <PageState message="Loading analyzed functions…" />}
          {functionsError && (
            <PageError title="Functions are unavailable" error={functionsError} compact />
          )}
          {!functionsLoading && !functionsError && (
            <>
              <div className="experiment-inline-fields">
                {method === "manual" ? (
                  <Field
                    label="Selected functions"
                    hint={`${selectedFunctions.length} of ${validFunctions.length} valid functions selected.`}
                  >
                    <input value={`${selectedFunctions.length} selected`} disabled />
                  </Field>
                ) : (
                  <Field
                    label="Number of functions"
                    hint={`${validFunctions.length} valid functions available.`}
                  >
                    <input
                      type="number"
                      min={1}
                      max={validFunctions.length}
                      value={functionCount}
                      onChange={(event) => setFunctionCount(Number(event.target.value))}
                    />
                  </Field>
                )}
                <Field
                  label="Random seed"
                  hint={
                    method === "random" ? "Used to make selection reproducible." : "None Available"
                  }
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
              {method === "manual" && (
                <div className="function-selection-list">
                  <div className="function-filters">
                    <input
                      type="search"
                      placeholder="Search function or file…"
                      value={searchTerm}
                      onChange={(event) => setSearchTerm(event.target.value)}
                    />
                    <span>{selectedFunctions.length} selected</span>
                  </div>
                  <div className="create-suite-function-list">
                    {filteredFunctions.map((item) => (
                      <label
                        key={item.key}
                        className={manualFunctionIds.includes(item.key) ? "is-selected" : ""}
                      >
                        <input
                          type="checkbox"
                          checked={manualFunctionIds.includes(item.key)}
                          onChange={() => toggleFunction(item.key)}
                        />
                        <span>
                          <strong>{item.name}</strong>
                          <small>
                            {item.projectName} · {item.file} · {item.branches} branches ·{" "}
                            {item.statements} statements
                          </small>
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              )}
              <Field label="Model">
                <select
                  value={model}
                  onChange={(event) => setModel(event.target.value as typeof model)}
                >
                  {models.map((item) => (
                    <option key={item}>{item}</option>
                  ))}
                </select>
              </Field>
            </>
          )}
        </section>
      )}

      {step === 2 && (
        <section className="platform-card wizard-panel">
          <div className="wizard-heading">
            <span className="eyebrow">Step 3</span>
            <h2>Review</h2>
            <p>Name this suite and confirm the exact job configuration.</p>
          </div>
          <dl className="definition-list create-suite-review">
            <div>
              <dt>Test Suite</dt>
              <dd>{name || "Not named"}</dd>
            </div>
            <div>
              <dt>Experiment</dt>
              <dd>{selectedEntry?.experimentName ?? "Not selected"}</dd>
            </div>
            <div>
              <dt>Prompt</dt>
              <dd>{resolvedPromptRole === "baseline" ? "Baseline prompt" : "Final Prompt"}</dd>
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
                {functionMethods.find((item) => item.id === method)?.title} ·{" "}
                {selectedFunctions.length} functions
              </dd>
            </div>
            <div>
              <dt>Random seed</dt>
              <dd>{method === "random" ? seed : "None Available"}</dd>
            </div>
            <div>
              <dt>Model</dt>
              <dd>{model}</dd>
            </div>
          </dl>
          {create.isError && (
            <p className="inline-validation-error" role="alert">
              {create.error instanceof Error
                ? create.error.message
                : "Test Suite could not be created."}
            </p>
          )}
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
            disabled={!canContinue || create.isPending}
            onClick={() => create.mutate()}
          >
            <FlaskConical size={15} /> {create.isPending ? "Creating…" : "Create Test Suite"}
          </button>
        )}
      </div>
    </div>
  );
}

function PageState({ message }: { message: string }) {
  return (
    <div className="page-state" role="status">
      {message}
    </div>
  );
}

function PageError({
  title,
  error,
  compact = false,
}: {
  title: string;
  error: unknown;
  compact?: boolean;
}) {
  const message = error instanceof Error ? error.message : "An unexpected request failed.";
  return (
    <section
      className={compact ? "inline-validation-error" : "page-state page-state-error"}
      role="alert"
    >
      <h2>{title}</h2>
      <p>{message}</p>
    </section>
  );
}
