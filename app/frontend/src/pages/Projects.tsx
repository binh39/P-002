import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useLocation } from "wouter";

import { useRepositories } from "@/app/providers";
import { Field, PageHeader, StatCard, StatusBadge } from "@/components/PlatformUI";
import type { CreateProjectInput, PythonProject } from "@/domain/projects";

const MAX_UPLOAD_BYTES = 100 * 1024 * 1024;

function projectTone(status: PythonProject["status"]) {
  if (status === "ready") return "success" as const;
  if (status === "failed") return "danger" as const;
  if (status === "analyzing") return "info" as const;
  return "warning" as const;
}

function cardTone(project: PythonProject) {
  if (project.runtimeStatus === "runtime_failed") return "danger" as const;
  if (["runtime_queued", "runtime_preparing"].includes(project.runtimeStatus ?? "")) {
    return "info" as const;
  }
  return projectTone(project.status);
}

function cardStatus(project: PythonProject) {
  if (project.runtimeStatus === "runtime_failed") return "Environment rejected";
  if (["runtime_queued", "runtime_preparing"].includes(project.runtimeStatus ?? "")) {
    return "Preparing environment";
  }
  if (project.runtimeStatus === "runtime_ready") return "Runtime ready";
  return projectStatus(project.status);
}

function projectStatus(status: PythonProject["status"]) {
  if (status === "ready") return "Ready";
  if (status === "failed") return "Analysis failed";
  if (status === "analyzing") return "Analyzing";
  return "Ready with warnings";
}

function ProjectCard({
  project,
  sample,
  open,
}: {
  project: PythonProject;
  sample: boolean;
  open: () => void;
}) {
  return (
    <article className="project-card">
      <div className="project-card-top">
        <div className="project-symbol">{project.name.slice(0, 2).toUpperCase()}</div>
        <StatusBadge tone={cardTone(project)}>{cardStatus(project)}</StatusBadge>
      </div>
      <h2>{project.name}</h2>
      <p>{project.description || "Imported Python source archive"}</p>
      <div className="project-meta-grid">
        <div>
          <span>Python</span>
          <strong>{project.python}</strong>
        </div>
        <div>
          <span>Snapshot</span>
          <strong>{project.commit}</strong>
        </div>
        <div>
          <span>Files</span>
          <strong>{project.files}</strong>
        </div>
        <div>
          <span>Functions</span>
          <strong>{project.functions}</strong>
        </div>
      </div>
      <div className="project-card-footer">
        <span>
          {sample
            ? "Bundled sample environment"
            : `${project.runtimeEnvironmentName || "Project runtime"} · private venv`}
        </span>
        <button onClick={open}>Open project →</button>
      </div>
    </article>
  );
}

export default function Projects() {
  const [, navigate] = useLocation();
  const { projects } = useRepositories();
  const queryClient = useQueryClient();
  const [showImport, setShowImport] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [branch, setBranch] = useState("main");
  const [commit, setCommit] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const samplesQuery = useQuery({
    queryKey: ["sample-projects"],
    queryFn: ({ signal }) => projects.listSamples(signal),
  });
  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: ({ signal }) => projects.list(signal),
    refetchInterval: (current) =>
      current.state.data?.some(
        (project) =>
          project.status === "analyzing" ||
          project.runtimeStatus === "runtime_queued" ||
          project.runtimeStatus === "runtime_preparing",
      )
        ? 2_000
        : false,
  });
  const createProject = useMutation({
    mutationFn: (input: CreateProjectInput) => projects.create(input),
    onSuccess: async (project) => {
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      setShowImport(false);
      navigate(`/projects/${project.id}`);
    },
  });

  const closeImport = () => {
    if (createProject.isPending) return;
    setShowImport(false);
    setValidationError(null);
    createProject.reset();
  };

  const submitImport = (event: FormEvent) => {
    event.preventDefault();
    const normalizedName = name.trim();
    const normalizedBranch = branch.trim();
    if (!normalizedName) {
      setValidationError("Enter a project name.");
      return;
    }
    if (!normalizedBranch) {
      setValidationError("Enter a branch or source label.");
      return;
    }
    if (!file) {
      setValidationError("Choose a ZIP archive.");
      return;
    }
    if (!file.name.toLowerCase().endsWith(".zip")) {
      setValidationError("Only .zip source archives are supported.");
      return;
    }
    if (file.size === 0) {
      setValidationError("The ZIP archive is empty.");
      return;
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      setValidationError("The ZIP archive must be 100 MB or smaller.");
      return;
    }
    setValidationError(null);
    createProject.mutate({
      name: normalizedName,
      description: description.trim(),
      branch: normalizedBranch,
      commit: commit.trim() || undefined,
      file,
    });
  };

  if (samplesQuery.isPending || projectsQuery.isPending) {
    return (
      <div className="page-state" role="status">
        Loading projects…
      </div>
    );
  }
  if (samplesQuery.isError || projectsQuery.isError) {
    const error = samplesQuery.error ?? projectsQuery.error;
    return (
      <div className="page-state page-state-error" role="alert">
        <h2>Projects are unavailable</h2>
        <p>{error instanceof Error ? error.message : "An unexpected error occurred."}</p>
        <button
          onClick={() => {
            void samplesQuery.refetch();
            void projectsQuery.refetch();
          }}
        >
          Try again
        </button>
      </div>
    );
  }

  const sampleProjects = samplesQuery.data;
  const importedProjects = projectsQuery.data;
  const allProjects = [...importedProjects, ...sampleProjects];
  const totalFunctions = allProjects.reduce((sum, project) => sum + project.functions, 0);

  return (
    <div className="platform-page projects-page">
      <PageHeader
        title="Projects"
        actions={
          <button
            className="primary-button"
            type="button"
            onClick={() => {
              createProject.reset();
              setValidationError(null);
              setShowImport(true);
            }}
          >
            + Create project
          </button>
        }
      />

      <div className="platform-stats-grid">
        <StatCard label="Projects" value={allProjects.length} />
        <StatCard
          label="Python files"
          value={allProjects.reduce((sum, project) => sum + project.files, 0)}
          tone="violet"
        />
        <StatCard label="Functions" value={totalFunctions} tone="green" />
        <StatCard
          label="Branches"
          value={allProjects.reduce((sum, project) => sum + project.branches, 0).toLocaleString()}
          tone="orange"
        />
      </div>

      <section className="project-section" aria-labelledby="my-projects-heading">
        <div className="project-section-heading">
          <div>
            <span className="eyebrow">Private workspace</span>
            <h2 id="my-projects-heading">My projects</h2>
          </div>
          <span>{importedProjects.length} imported</span>
        </div>
        {importedProjects.length === 0 ? (
          <div className="empty-state project-empty-state">
            <strong>No private projects yet</strong>
            <span>Upload a Python source ZIP to run safe static analysis.</span>
          </div>
        ) : (
          <div className="project-grid">
            {importedProjects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                sample={false}
                open={() => navigate(`/projects/${project.id}`)}
              />
            ))}
          </div>
        )}
      </section>

      <section className="project-section" aria-labelledby="sample-projects-heading">
        <div className="project-section-heading">
          <div>
            <span className="eyebrow">Experiment fixtures</span>
            <h2 id="sample-projects-heading">Sample projects</h2>
          </div>
          <span>{sampleProjects.length} bundled</span>
        </div>
        {sampleProjects.length === 0 ? (
          <div className="empty-state">The bundled sample catalog is unavailable.</div>
        ) : (
          <div className="project-grid">
            {sampleProjects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                sample
                open={() => navigate(`/projects/${project.id}`)}
              />
            ))}
          </div>
        )}
      </section>

      <div className="platform-callout">
        <div>
          <strong>Isolated runtime for every project</strong>
          <p>
            Each upload gets its own dependency-resolved venv. Projects can be optimized together
            even when their Python versions and dependencies differ.
          </p>
        </div>
        <button className="secondary-button" onClick={() => navigate("/experiments/new")}>
          Start optimization
        </button>
      </div>

      {showImport && (
        <div className="modal-backdrop" role="presentation" onMouseDown={closeImport}>
          <section
            className="project-import-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="import-project-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="project-import-heading">
              <div>
                <span className="eyebrow">Private source archive</span>
                <h2 id="import-project-title">Create project</h2>
                <p>
                  The archive is analyzed first, then admitted atomically into its own project
                  runtime.
                </p>
              </div>
              <button type="button" aria-label="Close project import" onClick={closeImport}>
                ×
              </button>
            </div>
            <form className="add-project-form" onSubmit={submitImport}>
              <Field label="Project name">
                <input
                  autoFocus
                  maxLength={100}
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="payments-service"
                  disabled={createProject.isPending}
                />
              </Field>
              <details className="project-advanced-details">
                <summary>
                  <span>Advanced details</span>
                  <small>Optional</small>
                </summary>
                <div className="project-advanced-fields">
                  <div className="form-grid">
                    <Field label="Branch or source label">
                      <input
                        maxLength={200}
                        value={branch}
                        onChange={(event) => setBranch(event.target.value)}
                        disabled={createProject.isPending}
                      />
                    </Field>
                    <Field label="Commit or version">
                      <input
                        maxLength={64}
                        value={commit}
                        onChange={(event) => setCommit(event.target.value)}
                        placeholder="Git SHA or release tag"
                        disabled={createProject.isPending}
                      />
                    </Field>
                  </div>
                  <Field label="Description">
                    <textarea
                      maxLength={500}
                      value={description}
                      onChange={(event) => setDescription(event.target.value)}
                      placeholder="What this Python project contains"
                      disabled={createProject.isPending}
                    />
                  </Field>
                </div>
              </details>
              <Field
                label="Python source ZIP"
                hint="Maximum 100 MB. Tests and generated folders are excluded from targets."
              >
                <div className="upload-field">
                  <input
                    type="file"
                    aria-label="Python source ZIP"
                    accept=".zip,application/zip,application/x-zip-compressed"
                    disabled={createProject.isPending}
                    onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                  />
                  {file && (
                    <span>
                      {file.name} · {(file.size / 1024 / 1024).toFixed(2)} MB
                    </span>
                  )}
                </div>
              </Field>
              {(validationError || createProject.isError) && (
                <div className="inline-validation-error" role="alert">
                  {validationError ??
                    (createProject.error instanceof Error
                      ? createProject.error.message
                      : "The project could not be created.")}
                </div>
              )}
              <div className="project-import-actions">
                <button
                  className="secondary-button"
                  type="button"
                  disabled={createProject.isPending}
                  onClick={closeImport}
                >
                  Cancel
                </button>
                <button className="primary-button" type="submit" disabled={createProject.isPending}>
                  {createProject.isPending
                    ? "Uploading and preparing environment…"
                    : "Upload and prepare"}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
