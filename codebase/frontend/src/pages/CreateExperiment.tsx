import { useMutation, useQueries, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useLocation } from "wouter";

import { useRepositories } from "@/app/providers";
import { Field, PageHeader, StatusBadge } from "@/components/PlatformUI";
import {
  defaultCloudSettings,
  defaultDatasetPercentages,
  percentagesAreValid,
  selectCandidateFunctions,
  splitFunctions,
  type CloudExperimentSettings,
  type DatasetPercentages,
  type DatasetSplit,
  type ExperimentFunction,
  type SamplingMethod,
} from "@/domain/experimentConfiguration";
import type { PythonProject } from "@/domain/projects";

const steps = ["Projects", "Functions", "Dataset", "Settings", "Review"];
const splitNames: DatasetSplit[] = ["train", "validation", "test"];
const maximumTargetsPerApiExperiment = 50;

function projectFunctionKey(projectId: string, functionId: string) {
  return `${projectId}:${functionId}`;
}

function formatSamplingMethod(method: SamplingMethod) {
  return {
    random: "Random",
    most_branches: "Most branches",
    most_statements: "Most statements",
    manual: "Manual",
  }[method];
}

export default function CreateExperiment() {
  const [, navigate] = useLocation();
  const { projects, experiments } = useRepositories();
  const [step, setStep] = useState(0);
  const [selectedProjectIds, setSelectedProjectIds] = useState<string[]>([]);
  const [experimentName, setExperimentName] = useState("");
  const [samplingMethod, setSamplingMethod] = useState<SamplingMethod>("random");
  const [sampleLimit, setSampleLimit] = useState(12);
  const [randomSeed, setRandomSeed] = useState(7);
  const [manualAssignments, setManualAssignments] = useState<Record<string, DatasetSplit>>({});
  const [percentages, setPercentages] = useState<DatasetPercentages>(defaultDatasetPercentages);
  const [settings, setSettings] = useState<CloudExperimentSettings>(defaultCloudSettings);
  const [search, setSearch] = useState("");
  const [projectFilter, setProjectFilter] = useState("all");

  const projectsQuery = useQuery({
    queryKey: ["sample-projects"],
    queryFn: ({ signal }) => projects.listSamples(signal),
  });
  const functionQueries = useQueries({
    queries: selectedProjectIds.map((projectId) => ({
      queryKey: ["projects", projectId, "functions"],
      queryFn: ({ signal }: { signal: AbortSignal }) => projects.listFunctions(projectId, signal),
      staleTime: 5 * 60_000,
    })),
  });

  const selectedProjects = useMemo(
    () => (projectsQuery.data ?? []).filter((project) => selectedProjectIds.includes(project.id)),
    [projectsQuery.data, selectedProjectIds],
  );
  const availableFunctions = useMemo<ExperimentFunction[]>(
    () =>
      functionQueries.flatMap((query, index) => {
        const project = selectedProjects.find((item) => item.id === selectedProjectIds[index]);
        if (!project || !query.data) return [];
        return query.data.map((item) => ({
          ...item,
          key: projectFunctionKey(project.id, item.id),
          projectName: project.name,
        }));
      }),
    [functionQueries, selectedProjectIds, selectedProjects],
  );
  const validFunctions = useMemo(
    () => availableFunctions.filter((item) => item.status === "Valid"),
    [availableFunctions],
  );
  const selectedFunctions = useMemo(() => {
    if (samplingMethod === "manual") {
      return validFunctions.filter((item) => manualAssignments[item.key] !== undefined);
    }
    return selectCandidateFunctions(
      validFunctions,
      samplingMethod,
      Math.min(sampleLimit, validFunctions.length),
      randomSeed,
    );
  }, [manualAssignments, randomSeed, sampleLimit, samplingMethod, validFunctions]);
  const dataset = useMemo(() => {
    if (samplingMethod === "manual") {
      return Object.fromEntries(
        splitNames.map((split) => [
          split,
          selectedFunctions.filter((item) => manualAssignments[item.key] === split),
        ]),
      ) as Record<DatasetSplit, ExperimentFunction[]>;
    }
    return splitFunctions(selectedFunctions, percentages, randomSeed);
  }, [manualAssignments, percentages, randomSeed, samplingMethod, selectedFunctions]);

  const functionsLoading = functionQueries.some((query) => query.isPending);
  const functionsError = functionQueries.find((query) => query.isError)?.error;
  const functionSelectionValid =
    selectedFunctions.length >= 3 &&
    Number.isInteger(randomSeed) &&
    randomSeed >= 0 &&
    (samplingMethod === "manual" || (Number.isInteger(sampleLimit) && sampleLimit >= 3));
  const datasetValid =
    percentagesAreValid(percentages) && splitNames.every((name) => dataset[name].length > 0);
  const settingsValid =
    settings.coverupModel.trim() !== "" &&
    settings.optimizeModel.trim() !== "" &&
    settings.maxAttempts >= 1 &&
    settings.repeatTests >= 0 &&
    settings.maxConcurrency >= 1 &&
    settings.maxConcurrency <= 32 &&
    settings.maxMetricCalls >= 3 &&
    settings.evaluationReplicates >= 1 &&
    settings.finalEvaluationReplicates >= 1 &&
    settings.reflectionTemperature >= 0 &&
    settings.reflectionTemperature <= 2;
  const canContinue = [
    selectedProjectIds.length > 0,
    !functionsLoading && !functionsError && functionSelectionValid,
    datasetValid,
    settingsValid,
    false,
  ][step];

  // The deployed API still stores one project per experiment and owns Cloud settings globally.
  // Keep the legacy-compatible path operational without pretending advanced configuration was saved.
  const apiCompatible =
    selectedProjectIds.length === 1 &&
    selectedFunctions.length <= maximumTargetsPerApiExperiment &&
    percentages.train === 60 &&
    percentages.validation === 20 &&
    percentages.test === 20 &&
    randomSeed === 7 &&
    JSON.stringify(settings) === JSON.stringify(defaultCloudSettings);

  const startBaseline = useMutation({
    mutationFn: async () => {
      const projectId = selectedProjectIds[0];
      const experiment = await experiments.create({
        projectId,
        name: experimentName.trim(),
        targetFunctionIds: selectedFunctions.map((item) => item.id),
      });
      return experiments.requestBaseline(experiment.id);
    },
    onSuccess: (run) => navigate(`/runs/${run.id}`),
  });

  const toggleProject = (project: PythonProject) => {
    setSelectedProjectIds((current) => {
      if (current.includes(project.id)) {
        setManualAssignments((assignments) =>
          Object.fromEntries(
            Object.entries(assignments).filter(([key]) => !key.startsWith(`${project.id}:`)),
          ),
        );
        return current.filter((id) => id !== project.id);
      }
      if (!experimentName.trim()) setExperimentName(`${project.name} prompt optimization`);
      return [...current, project.id];
    });
  };

  const setManualSplit = (key: string, split: DatasetSplit | "") => {
    setManualAssignments((current) => {
      if (!split)
        return Object.fromEntries(Object.entries(current).filter(([item]) => item !== key));
      return { ...current, [key]: split };
    });
  };

  if (projectsQuery.isPending) return <PageState message="Loading sample projects…" />;
  if (projectsQuery.isError) {
    return (
      <PageError
        title="Projects are unavailable"
        error={projectsQuery.error}
        onRetry={() => projectsQuery.refetch()}
      />
    );
  }

  return (
    <div className="platform-page wizard-page experiment-builder-page">
      <button className="back-link" onClick={() => navigate("/experiments")}>
        ← All experiments
      </button>
      <PageHeader
        eyebrow="New experiment"
        title="Configure prompt optimization"
        description="Build a reproducible multi-project dataset, then configure CoverUp and GEPA."
      />

      <ol className="wizard-steps experiment-wizard-steps">
        {steps.map((item, index) => (
          <li key={item} className={index === step ? "active" : index < step ? "complete" : ""}>
            <span>{index < step ? "✓" : index + 1}</span>
            <b>{item}</b>
          </li>
        ))}
      </ol>

      <div className="wizard-shell">
        <section className="wizard-content">
          {step === 0 && (
            <ProjectStep
              projects={projectsQuery.data}
              selectedProjectIds={selectedProjectIds}
              onToggle={toggleProject}
            />
          )}
          {step === 1 && (
            <FunctionsStep
              projects={selectedProjects}
              functions={validFunctions}
              loading={functionsLoading}
              error={functionsError}
              samplingMethod={samplingMethod}
              setSamplingMethod={setSamplingMethod}
              sampleLimit={sampleLimit}
              setSampleLimit={setSampleLimit}
              randomSeed={randomSeed}
              setRandomSeed={setRandomSeed}
              assignments={manualAssignments}
              setManualSplit={setManualSplit}
              search={search}
              setSearch={setSearch}
              projectFilter={projectFilter}
              setProjectFilter={setProjectFilter}
              retry={() => functionQueries.forEach((query) => void query.refetch())}
            />
          )}
          {step === 2 && (
            <DatasetStep
              percentages={percentages}
              setPercentages={setPercentages}
              dataset={dataset}
              manual={samplingMethod === "manual"}
              valid={datasetValid}
            />
          )}
          {step === 3 && <SettingsStep settings={settings} setSettings={setSettings} />}
          {step === 4 && (
            <ReviewStep
              experimentName={experimentName}
              setExperimentName={setExperimentName}
              projects={selectedProjects}
              dataset={dataset}
              samplingMethod={samplingMethod}
              randomSeed={randomSeed}
              percentages={percentages}
              settings={settings}
              apiCompatible={apiCompatible}
            />
          )}
        </section>

        <ExperimentSummary
          name={experimentName}
          projects={selectedProjects.length}
          available={validFunctions.length}
          selected={selectedFunctions.length}
          dataset={dataset}
          samplingMethod={samplingMethod}
          settings={settings}
        />
      </div>

      {startBaseline.isError && (
        <div className="auth-error wizard-submit-error" role="alert">
          {startBaseline.error instanceof Error
            ? startBaseline.error.message
            : "The experiment could not be started."}
        </div>
      )}

      <div className="wizard-actions">
        <button
          className="secondary-button"
          disabled={step === 0 || startBaseline.isPending}
          onClick={() => setStep((value) => Math.max(0, value - 1))}
        >
          Back
        </button>
        <span>
          Step {step + 1} of {steps.length}
        </span>
        {step < steps.length - 1 ? (
          <button
            className="primary-button"
            disabled={!canContinue}
            onClick={() => setStep((value) => value + 1)}
          >
            Continue →
          </button>
        ) : (
          <button
            className="primary-button"
            disabled={startBaseline.isPending || !experimentName.trim() || !apiCompatible}
            title={
              apiCompatible ? undefined : "The backend configuration API must be upgraded first"
            }
            onClick={() => startBaseline.mutate()}
          >
            {startBaseline.isPending ? "Creating and queueing…" : "Create and run baseline"}
          </button>
        )}
      </div>
    </div>
  );
}

function ProjectStep({
  projects,
  selectedProjectIds,
  onToggle,
}: {
  projects: PythonProject[];
  selectedProjectIds: string[];
  onToggle: (project: PythonProject) => void;
}) {
  const selectable = projects.filter((project) => ["ready", "warning"].includes(project.status));
  return (
    <>
      <WizardHeading
        step="Step 1"
        title="Choose projects"
        description="Select one or more immutable repositories. There is no UI project limit."
      />
      <div className="selection-toolbar">
        <span>{selectedProjectIds.length} project(s) selected</span>
        <button
          className="table-action"
          onClick={() =>
            selectable.filter((item) => !selectedProjectIds.includes(item.id)).forEach(onToggle)
          }
          disabled={selectedProjectIds.length === selectable.length}
        >
          Select all
        </button>
      </div>
      <div className="select-project-grid">
        {selectable.map((project) => {
          const active = selectedProjectIds.includes(project.id);
          return (
            <button
              key={project.id}
              className={active ? "select-project-card selected" : "select-project-card"}
              onClick={() => onToggle(project)}
              aria-pressed={active}
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
                  <dt>Commit</dt>
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
            </button>
          );
        })}
      </div>
    </>
  );
}

function FunctionsStep({
  projects,
  functions,
  loading,
  error,
  samplingMethod,
  setSamplingMethod,
  sampleLimit,
  setSampleLimit,
  randomSeed,
  setRandomSeed,
  assignments,
  setManualSplit,
  search,
  setSearch,
  projectFilter,
  setProjectFilter,
  retry,
}: {
  projects: PythonProject[];
  functions: ExperimentFunction[];
  loading: boolean;
  error: unknown;
  samplingMethod: SamplingMethod;
  setSamplingMethod: (method: SamplingMethod) => void;
  sampleLimit: number;
  setSampleLimit: (limit: number) => void;
  randomSeed: number;
  setRandomSeed: (seed: number) => void;
  assignments: Record<string, DatasetSplit>;
  setManualSplit: (key: string, split: DatasetSplit | "") => void;
  search: string;
  setSearch: (search: string) => void;
  projectFilter: string;
  setProjectFilter: (project: string) => void;
  retry: () => void;
}) {
  const methods: Array<{ id: SamplingMethod; title: string; description: string }> = [
    {
      id: "random",
      title: "Random",
      description: "Shuffle every valid function with the saved seed.",
    },
    {
      id: "most_branches",
      title: "Most branches",
      description: "Rank by branches, take the pool, then shuffle.",
    },
    {
      id: "most_statements",
      title: "Most statements",
      description: "Rank by statements, take the pool, then shuffle.",
    },
    {
      id: "manual",
      title: "Manual",
      description: "Choose functions and assign each to exactly one split.",
    },
  ];
  const filtered = functions.filter((item) => {
    const term = search.toLowerCase();
    return (
      (projectFilter === "all" || item.project === projectFilter) &&
      `${item.name} ${item.file} ${item.className}`.toLowerCase().includes(term)
    );
  });

  return (
    <>
      <WizardHeading
        step="Step 2"
        title="Select candidate functions"
        description="Choose how the dataset candidate pool is built from all selected projects."
      />
      <div className="sampling-method-grid">
        {methods.map((method) => (
          <button
            key={method.id}
            className={samplingMethod === method.id ? "sampling-card selected" : "sampling-card"}
            onClick={() => setSamplingMethod(method.id)}
            aria-pressed={samplingMethod === method.id}
          >
            <span className="radio-dot" />
            <strong>{method.title}</strong>
            <small>{method.description}</small>
          </button>
        ))}
      </div>
      {loading && <PageState message="Loading analyzed functions…" />}
      {error && (
        <PageError title="Functions are unavailable" error={error} onRetry={retry} compact />
      )}
      {!loading && !error && (
        <>
          <div className="experiment-inline-fields">
            {samplingMethod !== "manual" && (
              <Field
                label="Candidate functions"
                hint={`${functions.length} valid functions available`}
              >
                <input
                  type="number"
                  min={3}
                  max={Math.max(3, functions.length)}
                  value={sampleLimit}
                  onChange={(event) => setSampleLimit(Number(event.target.value))}
                />
              </Field>
            )}
            <Field label="Random seed" hint="Same snapshot + seed produces the same dataset.">
              <input
                type="number"
                min={0}
                value={randomSeed}
                onChange={(event) => setRandomSeed(Number(event.target.value))}
              />
            </Field>
          </div>
          {samplingMethod === "manual" && (
            <>
              <div className="function-filters">
                <input
                  type="search"
                  placeholder="Search function or file…"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                />
                <select
                  value={projectFilter}
                  onChange={(event) => setProjectFilter(event.target.value)}
                >
                  <option value="all">All projects</option>
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </select>
                <span>{Object.keys(assignments).length} assigned</span>
              </div>
              <FunctionTable
                functions={filtered}
                assignments={assignments}
                setManualSplit={setManualSplit}
              />
            </>
          )}
          {samplingMethod !== "manual" && (
            <div className="method-rule-note">
              <strong>Selection rule</strong>
              <span>
                {samplingMethod === "random"
                  ? "Valid functions are shuffled directly."
                  : "Functions are ranked first; only the selected candidate pool is shuffled before splitting."}
              </span>
            </div>
          )}
        </>
      )}
    </>
  );
}

function FunctionTable({
  functions,
  assignments,
  setManualSplit,
}: {
  functions: ExperimentFunction[];
  assignments: Record<string, DatasetSplit>;
  setManualSplit: (key: string, split: DatasetSplit | "") => void;
}) {
  return (
    <div className="table-scroll function-selection-table">
      <table className="platform-table">
        <thead>
          <tr>
            <th>Project</th>
            <th>File / function</th>
            <th>LOC</th>
            <th>Statements</th>
            <th>Branches</th>
            <th>Dataset split</th>
          </tr>
        </thead>
        <tbody>
          {functions.map((item) => (
            <tr key={item.key} className={assignments[item.key] ? "selected-function-row" : ""}>
              <td>{item.projectName}</td>
              <td>
                <strong>{item.file}</strong>
                <small>
                  <code>{item.name}</code>
                </small>
              </td>
              <td>{item.loc}</td>
              <td>{item.statements}</td>
              <td>{item.branches}</td>
              <td>
                <select
                  aria-label={`Dataset split for ${item.name}`}
                  value={assignments[item.key] ?? ""}
                  onChange={(event) =>
                    setManualSplit(item.key, event.target.value as DatasetSplit | "")
                  }
                >
                  <option value="">Not selected</option>
                  <option value="train">Train</option>
                  <option value="validation">Validation</option>
                  <option value="test">Test</option>
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DatasetStep({
  percentages,
  setPercentages,
  dataset,
  manual,
  valid,
}: {
  percentages: DatasetPercentages;
  setPercentages: (percentages: DatasetPercentages) => void;
  dataset: Record<DatasetSplit, ExperimentFunction[]>;
  manual: boolean;
  valid: boolean;
}) {
  const [activeSplit, setActiveSplit] = useState<DatasetSplit>("train");
  return (
    <>
      <WizardHeading
        step="Step 3"
        title="Build the dataset snapshot"
        description="Keep test isolated from GEPA search and preview the exact disjoint split."
      />
      {manual ? (
        <div className="method-rule-note">
          <strong>Manual split</strong>
          <span>Percentages are informational; assignments from Step 2 are authoritative.</span>
        </div>
      ) : (
        <div className="split-config-grid">
          {splitNames.map((name) => (
            <Field
              key={name}
              label={`${name === "validation" ? "Validation" : name[0].toUpperCase() + name.slice(1)} (%)`}
            >
              <input
                type="number"
                min={0}
                max={100}
                value={percentages[name]}
                onChange={(event) =>
                  setPercentages({ ...percentages, [name]: Number(event.target.value) })
                }
              />
            </Field>
          ))}
        </div>
      )}
      {!valid && (
        <div className="inline-validation-error">
          Percentages must total 100%, test must be greater than 0, and every split needs at least
          one function.
        </div>
      )}
      <div className="dataset-snapshot-stats">
        {splitNames.map((name) => (
          <DatasetStat key={name} name={name} functions={dataset[name]} />
        ))}
      </div>
      <div className="dataset-tabs" role="tablist">
        {splitNames.map((name) => (
          <button
            key={name}
            className={activeSplit === name ? "active" : ""}
            onClick={() => setActiveSplit(name)}
          >
            {name === "validation" ? "Validation" : name[0].toUpperCase() + name.slice(1)} (
            {dataset[name].length})
          </button>
        ))}
      </div>
      <div className="dataset-preview-list">
        {dataset[activeSplit].map((item) => (
          <div key={item.key}>
            <span>
              <strong>{item.projectName}</strong>
              <code>{item.name}</code>
            </span>
            <small>
              {item.file} · {item.statements} stmt · {item.branches} branches
            </small>
          </div>
        ))}
      </div>
      {activeSplit === "test" && (
        <div className="holdout-notice">
          <strong>Locked holdout</strong> GEPA never sees this split during proposal or candidate
          selection.
        </div>
      )}
    </>
  );
}

function DatasetStat({ name, functions }: { name: DatasetSplit; functions: ExperimentFunction[] }) {
  const statements = functions.reduce((sum, item) => sum + item.statements, 0);
  const branches = functions.reduce((sum, item) => sum + item.branches, 0);
  return (
    <section>
      <span>{name}</span>
      <strong>{functions.length}</strong>
      <small>
        {statements} statements · {branches} branches
      </small>
    </section>
  );
}

function SettingsStep({
  settings,
  setSettings,
}: {
  settings: CloudExperimentSettings;
  setSettings: (settings: CloudExperimentSettings) => void;
}) {
  const update = <Key extends keyof CloudExperimentSettings>(
    key: Key,
    value: CloudExperimentSettings[Key],
  ) => setSettings({ ...settings, [key]: value });
  return (
    <>
      <WizardHeading
        step="Step 4"
        title="Configure CoverUp and GEPA"
        description="Runtime controls that affect cost, reproducibility and optimization quality."
      />
      <section className="settings-section">
        <div className="settings-section-title">
          <span>01</span>
          <div>
            <h3>Models</h3>
            <p>Vertex/LiteLLM model identifiers used by generation and reflection.</p>
          </div>
        </div>
        <div className="settings-form-grid">
          <Field label="COVERUP_MODEL" hint="Generates candidate unit tests.">
            <input
              list="experiment-models"
              value={settings.coverupModel}
              onChange={(event) => update("coverupModel", event.target.value)}
            />
          </Field>
          <Field label="OPTIMIZE_MODEL" hint="Reflects and proposes prompt changes.">
            <input
              list="experiment-models"
              value={settings.optimizeModel}
              onChange={(event) => update("optimizeModel", event.target.value)}
            />
          </Field>
          <datalist id="experiment-models">
            <option value="vertex_ai/gemini-3.6-flash" />
            <option value="vertex_ai/gemini-2.5-flash" />
            <option value="vertex_ai/gemini-2.5-pro" />
          </datalist>
        </div>
      </section>
      <section className="settings-section">
        <div className="settings-section-title">
          <span>02</span>
          <div>
            <h3>CoverUp execution</h3>
            <p>Retry, stability and quota controls.</p>
          </div>
        </div>
        <div className="settings-form-grid settings-form-grid-3">
          <NumberField
            label="Max attempts"
            value={settings.maxAttempts}
            min={1}
            max={20}
            onChange={(value) => update("maxAttempts", value)}
          />
          <NumberField
            label="Repeat tests"
            value={settings.repeatTests}
            min={0}
            max={20}
            onChange={(value) => update("repeatTests", value)}
          />
          <NumberField
            label="Max concurrency"
            value={settings.maxConcurrency}
            min={1}
            max={32}
            onChange={(value) => update("maxConcurrency", value)}
          />
          <Field label="Rate limit (tokens/min)" hint="Blank uses provider quota.">
            <input
              type="number"
              min={1}
              value={settings.rateLimit ?? ""}
              onChange={(event) =>
                update("rateLimit", event.target.value ? Number(event.target.value) : null)
              }
            />
          </Field>
          <Field label="Additional pytest args" hint="Passed to isolated coverage runs.">
            <input
              value={settings.pytestArgs}
              placeholder="-m 'not slow'"
              onChange={(event) => update("pytestArgs", event.target.value)}
            />
          </Field>
        </div>
      </section>
      <section className="settings-section">
        <div className="settings-section-title">
          <span>03</span>
          <div>
            <h3>GEPA search budget</h3>
            <p>Metric calls are real prompt-symbol evaluations and directly affect cost.</p>
          </div>
        </div>
        <div className="settings-form-grid settings-form-grid-3">
          <Field label="Budget mode">
            <select
              value={settings.budgetMode}
              onChange={(event) => {
                const mode = event.target.value as CloudExperimentSettings["budgetMode"];
                setSettings({
                  ...settings,
                  budgetMode: mode,
                  maxMetricCalls:
                    mode === "light"
                      ? 120
                      : mode === "medium"
                        ? 300
                        : mode === "heavy"
                          ? 600
                          : settings.maxMetricCalls,
                });
              }}
            >
              <option value="light">Light · 120</option>
              <option value="medium">Medium · 300</option>
              <option value="heavy">Heavy · 600</option>
              <option value="custom">Custom</option>
            </select>
          </Field>
          <NumberField
            label="Max metric calls"
            value={settings.maxMetricCalls}
            min={3}
            max={2200}
            disabled={settings.budgetMode !== "custom"}
            onChange={(value) => update("maxMetricCalls", value)}
          />
          <NumberField
            label="Evaluation replicates"
            value={settings.evaluationReplicates}
            min={1}
            max={10}
            onChange={(value) => update("evaluationReplicates", value)}
          />
          <NumberField
            label="Final test replicates"
            value={settings.finalEvaluationReplicates}
            min={1}
            max={10}
            onChange={(value) => update("finalEvaluationReplicates", value)}
          />
          <Field label="Reflection temperature" hint="0.7 is recommended for proposal diversity.">
            <input
              type="number"
              min={0}
              max={2}
              step={0.1}
              value={settings.reflectionTemperature}
              onChange={(event) => update("reflectionTemperature", Number(event.target.value))}
            />
          </Field>
        </div>
      </section>
      <section className="settings-section evaluation-protocol-section">
        <div className="settings-section-title">
          <span>04</span>
          <div>
            <h3>Evaluation protocol</h3>
            <p>Fixed invariants from the deployed Cloud pipeline.</p>
          </div>
        </div>
        <div className="protocol-grid">
          <div>
            <span>Target metric</span>
            <strong>Coverage score</strong>
            <small>40% statement + 60% branch</small>
          </div>
          <div>
            <span>Holdout</span>
            <strong>Test split</strong>
            <small>Never visible to GEPA search</small>
          </div>
          <div>
            <span>Promotion</span>
            <strong>Strict improvement</strong>
            <small>Ties keep the baseline prompt</small>
          </div>
        </div>
      </section>
      <div className="holdout-notice">
        <strong>Promotion gate:</strong> the candidate is promoted only when it is strictly better
        than its paired baseline on the locked test split.
      </div>
    </>
  );
}

function NumberField({
  label,
  value,
  min,
  max,
  disabled = false,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  disabled?: boolean;
  onChange: (value: number) => void;
}) {
  return (
    <Field label={label}>
      <input
        type="number"
        min={min}
        max={max}
        disabled={disabled}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </Field>
  );
}

function ReviewStep({
  experimentName,
  setExperimentName,
  projects,
  dataset,
  samplingMethod,
  randomSeed,
  percentages,
  settings,
  apiCompatible,
}: {
  experimentName: string;
  setExperimentName: (name: string) => void;
  projects: PythonProject[];
  dataset: Record<DatasetSplit, ExperimentFunction[]>;
  samplingMethod: SamplingMethod;
  randomSeed: number;
  percentages: DatasetPercentages;
  settings: CloudExperimentSettings;
  apiCompatible: boolean;
}) {
  return (
    <>
      <WizardHeading
        step="Step 5"
        title="Review and launch"
        description="Verify the reproducibility snapshot before starting paid Cloud work."
      />
      <Field label="Experiment name" hint="Up to 120 characters.">
        <input
          value={experimentName}
          maxLength={120}
          onChange={(event) => setExperimentName(event.target.value)}
        />
      </Field>
      {!apiCompatible && (
        <div className="api-compatibility-warning" role="alert">
          <strong>Backend contract update required</strong>
          <p>
            The current API accepts one project, up to 50 targets, a fixed 60/20/20 split with seed
            7, and deployed global model settings. This advanced configuration is intentionally not
            submitted as if it were supported.
          </p>
        </div>
      )}
      <div className="review-grid experiment-review-grid">
        <ReviewCard
          title="Project snapshots"
          rows={projects.map((project) => [project.name, `${project.branch} · ${project.commit}`])}
        />
        <ReviewCard
          title="Dataset"
          rows={[
            ["Sampling", formatSamplingMethod(samplingMethod)],
            ["Seed", String(randomSeed)],
            ["Percentages", `${percentages.train}/${percentages.validation}/${percentages.test}`],
            ...splitNames.map(
              (name) => [name, `${dataset[name].length} functions`] as [string, string],
            ),
          ]}
        />
        <ReviewCard
          title="Models"
          rows={[
            ["CoverUp", settings.coverupModel],
            ["Optimizer", settings.optimizeModel],
            ["Replicates", String(settings.evaluationReplicates)],
            ["Final replicates", String(settings.finalEvaluationReplicates)],
          ]}
        />
        <ReviewCard
          title="Execution"
          rows={[
            ["Attempts", String(settings.maxAttempts)],
            ["Repeat tests", String(settings.repeatTests)],
            ["Concurrency", String(settings.maxConcurrency)],
            ["Metric calls", String(settings.maxMetricCalls)],
          ]}
        />
      </div>
      <section className="validation-box">
        <h3>Pipeline guarantees</h3>
        <div>
          <span>✓</span>Disjoint, deterministic dataset snapshot
        </div>
        <div>
          <span>✓</span>Test holdout excluded from GEPA search
        </div>
        <div>
          <span>✓</span>Paired baseline/candidate promotion gate
        </div>
      </section>
    </>
  );
}

function ReviewCard({ title, rows }: { title: string; rows: Array<[string, string]> }) {
  return (
    <section className="review-section">
      <h3>{title}</h3>
      <dl className="definition-list">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function ExperimentSummary({
  name,
  projects,
  available,
  selected,
  dataset,
  samplingMethod,
  settings,
}: {
  name: string;
  projects: number;
  available: number;
  selected: number;
  dataset: Record<DatasetSplit, ExperimentFunction[]>;
  samplingMethod: SamplingMethod;
  settings: CloudExperimentSettings;
}) {
  return (
    <aside className="wizard-summary">
      <span className="eyebrow">Live configuration</span>
      <h3>{name.trim() || "Untitled experiment"}</h3>
      <dl>
        <div>
          <dt>Projects</dt>
          <dd>{projects}</dd>
        </div>
        <div>
          <dt>Available</dt>
          <dd>{available}</dd>
        </div>
        <div>
          <dt>Selected</dt>
          <dd>{selected}</dd>
        </div>
        <div>
          <dt>Sampling</dt>
          <dd>{formatSamplingMethod(samplingMethod)}</dd>
        </div>
        <div>
          <dt>Train / Val / Test</dt>
          <dd>
            {dataset.train.length} / {dataset.validation.length} / {dataset.test.length}
          </dd>
        </div>
        <div>
          <dt>Budget</dt>
          <dd>
            {settings.budgetMode === "custom" ? settings.maxMetricCalls : settings.budgetMode}
          </dd>
        </div>
      </dl>
      <div
        className={selected >= 3 && dataset.test.length > 0 ? "summary-valid" : "summary-invalid"}
      >
        {selected >= 3 && dataset.test.length > 0
          ? "✓ Dataset is optimization-ready"
          : "Select at least 3 functions across non-empty splits"}
      </div>
    </aside>
  );
}

function WizardHeading({
  step,
  title,
  description,
}: {
  step: string;
  title: string;
  description: string;
}) {
  return (
    <div className="wizard-heading">
      <span className="eyebrow">{step}</span>
      <h2>{title}</h2>
      <p>{description}</p>
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
  onRetry,
  compact = false,
}: {
  title: string;
  error: unknown;
  onRetry: () => void;
  compact?: boolean;
}) {
  return (
    <div
      className={`page-state page-state-error${compact ? " page-state-compact" : ""}`}
      role="alert"
    >
      <h2>{title}</h2>
      <p>{error instanceof Error ? error.message : "An unexpected error occurred."}</p>
      <button onClick={onRetry}>Try again</button>
    </div>
  );
}
