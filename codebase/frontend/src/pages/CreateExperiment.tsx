import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useLocation } from "wouter";

import { useRepositories } from "@/app/providers";
import { Field, PageHeader, StatusBadge } from "@/components/PlatformUI";
import type { ProjectFunction, PythonProject } from "@/domain/projects";

const steps = ["Project", "Functions", "Review"];
const maximumTargets = 50;

export default function CreateExperiment() {
  const [, navigate] = useLocation();
  const { projects, experiments } = useRepositories();
  const [step, setStep] = useState(0);
  const [projectId, setProjectId] = useState("");
  const [experimentName, setExperimentName] = useState("");
  const [selectedFunctionIds, setSelectedFunctionIds] = useState<string[]>([]);
  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: ({ signal }) => projects.list(signal),
  });
  const functionsQuery = useQuery({
    queryKey: ["projects", projectId, "functions"],
    queryFn: ({ signal }) => projects.listFunctions(projectId, signal),
    enabled: projectId !== "",
  });
  const startBaseline = useMutation({
    mutationFn: async () => {
      const experiment = await experiments.create({
        projectId,
        name: experimentName.trim(),
        targetFunctionIds: selectedFunctionIds,
      });
      return experiments.requestBaseline(experiment.id);
    },
    onSuccess: (run) => navigate(`/runs/${run.id}`),
  });

  const selectedProject = projectsQuery.data?.find((project) => project.id === projectId);
  const functions = useMemo(() => functionsQuery.data ?? [], [functionsQuery.data]);
  const selectedFunctions = useMemo(
    () => functions.filter((item) => selectedFunctionIds.includes(item.id)),
    [functions, selectedFunctionIds],
  );
  const canContinue =
    (step === 0 && selectedProject !== undefined) ||
    (step === 1 && selectedFunctionIds.length > 0 && selectedFunctionIds.length <= maximumTargets);

  const selectProject = (project: PythonProject) => {
    setProjectId(project.id);
    setSelectedFunctionIds([]);
    if (!experimentName.trim()) setExperimentName(`${project.name} baseline`);
  };

  const toggleFunction = (functionId: string) => {
    setSelectedFunctionIds((current) =>
      current.includes(functionId)
        ? current.filter((id) => id !== functionId)
        : current.length < maximumTargets
          ? [...current, functionId]
          : current,
    );
  };

  if (projectsQuery.isPending) return <PageState message="Loading Python projects…" />;
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
    <div className="platform-page wizard-page">
      <button className="back-link" onClick={() => navigate("/experiments")}>
        ← All experiments
      </button>
      <PageHeader
        eyebrow="New experiment"
        title="Create a baseline evaluation"
        description="Select one analyzed project and the functions CoverUp should evaluate."
      />

      <ol className="wizard-steps wizard-steps-compact">
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
              selectedProjectId={projectId}
              onSelect={selectProject}
            />
          )}
          {step === 1 && (
            <FunctionsStep
              project={selectedProject}
              functions={functions}
              loading={functionsQuery.isPending}
              error={functionsQuery.error}
              selected={selectedFunctionIds}
              onToggle={toggleFunction}
              onSelectAll={() =>
                setSelectedFunctionIds(
                  functions
                    .filter((item) => item.status === "Valid")
                    .slice(0, maximumTargets)
                    .map((item) => item.id),
                )
              }
              onClear={() => setSelectedFunctionIds([])}
              onRetry={() => functionsQuery.refetch()}
            />
          )}
          {step === 2 && (
            <ReviewStep
              project={selectedProject}
              functions={selectedFunctions}
              experimentName={experimentName}
              setExperimentName={setExperimentName}
            />
          )}
        </section>

        <aside className="wizard-summary">
          <span className="eyebrow">Live configuration</span>
          <h3>{experimentName.trim() || "Untitled experiment"}</h3>
          <dl>
            <div>
              <dt>Project</dt>
              <dd>{selectedProject?.name ?? "Not selected"}</dd>
            </div>
            <div>
              <dt>Functions</dt>
              <dd>{selectedFunctionIds.length}</dd>
            </div>
            <div>
              <dt>Maximum</dt>
              <dd>{maximumTargets}</dd>
            </div>
            <div>
              <dt>Execution</dt>
              <dd>Cloud Run Job</dd>
            </div>
          </dl>
          <div className={selectedFunctionIds.length > 0 ? "summary-valid" : "summary-invalid"}>
            {selectedFunctionIds.length >= 3
              ? "✓ Eligible for the later optimization stage"
              : selectedFunctionIds.length > 0
                ? "Baseline ready; select at least 3 for later optimization"
                : "Select at least one function"}
          </div>
        </aside>
      </div>

      {startBaseline.isError && (
        <div className="auth-error wizard-submit-error" role="alert">
          {startBaseline.error instanceof Error
            ? startBaseline.error.message
            : "The baseline could not be started."}
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
            disabled={
              startBaseline.isPending || !experimentName.trim() || selectedFunctionIds.length === 0
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
  selectedProjectId,
  onSelect,
}: {
  projects: PythonProject[];
  selectedProjectId: string;
  onSelect: (project: PythonProject) => void;
}) {
  const selectable = projects.filter(
    (project) => project.status === "ready" || project.status === "warning",
  );
  return (
    <>
      <div className="wizard-heading">
        <span className="eyebrow">Step 1</span>
        <h2>Select a Python project</h2>
        <p>Experiments use one immutable analyzed project snapshot.</p>
      </div>
      {selectable.length === 0 ? (
        <div className="empty-state">No analyzed project is ready for an experiment.</div>
      ) : (
        <div className="select-project-grid">
          {selectable.map((project) => {
            const active = selectedProjectId === project.id;
            return (
              <button
                key={project.id}
                className={active ? "select-project-card selected" : "select-project-card"}
                onClick={() => onSelect(project)}
                aria-pressed={active}
              >
                <span className="project-checkbox">{active ? "✓" : ""}</span>
                <div>
                  <h3>{project.name}</h3>
                  <p>{project.description || "No description provided."}</p>
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
              </button>
            );
          })}
        </div>
      )}
    </>
  );
}

function FunctionsStep({
  project,
  functions,
  loading,
  error,
  selected,
  onToggle,
  onSelectAll,
  onClear,
  onRetry,
}: {
  project?: PythonProject;
  functions: ProjectFunction[];
  loading: boolean;
  error: Error | null;
  selected: string[];
  onToggle: (id: string) => void;
  onSelectAll: () => void;
  onClear: () => void;
  onRetry: () => void;
}) {
  return (
    <>
      <div className="wizard-heading">
        <span className="eyebrow">Step 2</span>
        <h2>Select target functions</h2>
        <p>
          Choose up to {maximumTargets} functions from {project?.name} for this baseline.
        </p>
      </div>
      <div className="selection-toolbar">
        <span>{selected.length} selected</span>
        <div>
          <button className="table-action" onClick={onSelectAll} disabled={loading}>
            Select valid (max {maximumTargets})
          </button>
          <button className="table-action" onClick={onClear} disabled={selected.length === 0}>
            Clear
          </button>
        </div>
      </div>
      {loading && <PageState message="Loading analyzed functions…" />}
      {error && (
        <PageError title="Functions are unavailable" error={error} onRetry={onRetry} compact />
      )}
      {!loading && !error && functions.length === 0 && (
        <div className="empty-state">This project has no analyzed functions.</div>
      )}
      {!loading && !error && functions.length > 0 && (
        <div className="table-scroll function-selection-table">
          <table className="platform-table">
            <thead>
              <tr>
                <th>Select</th>
                <th>File / class</th>
                <th>Function</th>
                <th>Lines</th>
                <th>Statements</th>
                <th>Branches</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {functions.map((item) => {
                const active = selected.includes(item.id);
                const limitReached = selected.length >= maximumTargets && !active;
                return (
                  <tr key={item.id} className={active ? "selected-function-row" : ""}>
                    <td>
                      <input
                        type="checkbox"
                        aria-label={`Select ${item.name}`}
                        checked={active}
                        disabled={limitReached}
                        onChange={() => onToggle(item.id)}
                      />
                    </td>
                    <td>
                      <strong>{item.file}</strong>
                      <small>{item.className || "Module function"}</small>
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
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function ReviewStep({
  project,
  functions,
  experimentName,
  setExperimentName,
}: {
  project?: PythonProject;
  functions: ProjectFunction[];
  experimentName: string;
  setExperimentName: (value: string) => void;
}) {
  return (
    <>
      <div className="wizard-heading">
        <span className="eyebrow">Step 3</span>
        <h2>Review and start baseline</h2>
        <p>The backend will snapshot the targets and create deterministic dataset splits.</p>
      </div>
      <Field label="Experiment name" hint="Used to identify this immutable evaluation.">
        <input
          value={experimentName}
          maxLength={120}
          onChange={(event) => setExperimentName(event.target.value)}
        />
      </Field>
      <div className="review-grid baseline-review-grid">
        <section className="review-section">
          <h3>Project snapshot</h3>
          <dl className="definition-list">
            <div>
              <dt>Project</dt>
              <dd>{project?.name}</dd>
            </div>
            <div>
              <dt>Branch</dt>
              <dd>{project?.branch}</dd>
            </div>
            <div>
              <dt>Commit</dt>
              <dd>{project?.commit}</dd>
            </div>
            <div>
              <dt>Python</dt>
              <dd>{project?.python}</dd>
            </div>
          </dl>
        </section>
        <section className="review-section">
          <h3>Baseline scope</h3>
          <dl className="definition-list">
            <div>
              <dt>Functions</dt>
              <dd>{functions.length}</dd>
            </div>
            <div>
              <dt>Statements</dt>
              <dd>{functions.reduce((sum, item) => sum + item.statements, 0)}</dd>
            </div>
            <div>
              <dt>Branches</dt>
              <dd>{functions.reduce((sum, item) => sum + item.branches, 0)}</dd>
            </div>
            <div>
              <dt>Runner</dt>
              <dd>Isolated Cloud Run Job</dd>
            </div>
          </dl>
        </section>
      </div>
      <section className="validation-box">
        <h3>What happens next</h3>
        <div>
          <span>✓</span>Create the experiment and immutable target snapshot
        </div>
        <div>
          <span>✓</span>Queue the baseline through Cloud Tasks
        </div>
        <div>
          <span>✓</span>Poll the run and publish coverage artifacts
        </div>
      </section>
    </>
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
