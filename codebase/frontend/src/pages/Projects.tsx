import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useLocation } from "wouter";

import { useRepositories } from "@/app/providers";
import { PageHeader, StatCard, StatusBadge } from "@/components/PlatformUI";
import type { CreateProjectInput } from "@/domain/projects";

export default function Projects() {
  const [, navigate] = useLocation();
  const { projects } = useRepositories();
  const queryClient = useQueryClient();
  const [isAdding, setIsAdding] = useState(false);
  const query = useQuery({
    queryKey: ["projects"],
    queryFn: ({ signal }) => projects.list(signal),
    refetchInterval: (current) =>
      current.state.data?.some((project) => project.status === "analyzing") ? 2_000 : false,
  });
  const createProject = useMutation({
    mutationFn: (input: CreateProjectInput) => projects.create(input),
    onSuccess: async (project) => {
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      setIsAdding(false);
      navigate(`/projects/${project.id}`);
    },
  });

  const handleCreate = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const file = form.get("archive");
    if (!(file instanceof File) || file.size === 0) return;
    createProject.mutate({
      name: String(form.get("name") ?? "").trim(),
      description: String(form.get("description") ?? "").trim(),
      branch: String(form.get("branch") ?? "main").trim(),
      commit: String(form.get("commit") ?? "").trim() || undefined,
      file,
    });
  };

  if (query.isPending)
    return (
      <div className="page-state" role="status">
        Loading Python projectsâ€¦
      </div>
    );
  if (query.isError)
    return (
      <div className="page-state page-state-error" role="alert">
        <h2>Projects are unavailable</h2>
        <p>
          {query.error instanceof Error ? query.error.message : "An unexpected error occurred."}
        </p>
        <button onClick={() => query.refetch()}>Try again</button>
      </div>
    );

  const pythonProjects = query.data;
  const totalFunctions = pythonProjects.reduce((sum, project) => sum + project.functions, 0);

  return (
    <div className="platform-page">
      <PageHeader
        eyebrow="Code inventory"
        title="Python Projects"
        description="Manage source versions, runtime configuration and function analysis."
        actions={
          <button className="primary-button" onClick={() => setIsAdding(true)}>
            + Add project
          </button>
        }
      />

      <div className="platform-stats-grid">
        <StatCard
          label="Projects"
          value={pythonProjects.length}
          detail={`${pythonProjects.filter((item) => item.status === "ready").length} ready`}
        />
        <StatCard
          label="Python files"
          value={pythonProjects.reduce((sum, project) => sum + project.files, 0)}
          detail="Across all versions"
          tone="violet"
        />
        <StatCard
          label="Functions"
          value={totalFunctions}
          detail="Analyzed with Python AST"
          tone="green"
        />
        <StatCard
          label="Branches"
          value={pythonProjects
            .reduce((sum, project) => sum + project.branches, 0)
            .toLocaleString()}
          detail="Coverage candidates"
          tone="orange"
        />
      </div>

      {pythonProjects.length === 0 ? (
        <div className="empty-state">
          No projects yet. Upload a Python ZIP to create the first one.
        </div>
      ) : (
        <div className="project-grid">
          {pythonProjects.map((project) => (
            <article className="project-card" key={project.id}>
              <div className="project-card-top">
                <div className="project-symbol">{project.name.slice(0, 2).toUpperCase()}</div>
                <StatusBadge tone={project.status === "ready" ? "success" : "warning"}>
                  {project.status === "ready"
                    ? "Ready"
                    : project.status === "analyzing"
                      ? "Analysis pending"
                      : project.status === "failed"
                        ? "Analysis failed"
                        : "Needs attention"}
                </StatusBadge>
              </div>
              <h2>{project.name}</h2>
              <p>{project.description}</p>
              <div className="project-meta-grid">
                <div>
                  <span>Python</span>
                  <strong>{project.python}</strong>
                </div>
                <div>
                  <span>Version</span>
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
                <span>{project.analyzedAt}</span>
                <button onClick={() => navigate(`/projects/${project.id}`)}>
                  Open project â†’
                </button>
              </div>
            </article>
          ))}
        </div>
      )}

      <div className="platform-callout">
        <div>
          <strong>Project analysis is version-aware</strong>
          <p>
            A new commit or configuration change creates a new analysis snapshot. Existing
            experiment results remain reproducible.
          </p>
        </div>
        <button className="secondary-button">View analysis queue</button>
      </div>

      {isAdding && (
        <div className="drawer-backdrop" onClick={() => setIsAdding(false)}>
          <aside
            className="source-drawer add-project-drawer"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="drawer-heading">
              <div>
                <span className="eyebrow">New source snapshot</span>
                <h2>Add Python project</h2>
                <p>Upload a ZIP archive and record the exact source version.</p>
              </div>
              <button onClick={() => setIsAdding(false)}>Ã—</button>
            </div>
            <form className="add-project-form" onSubmit={handleCreate}>
              <label className="platform-field">
                <span>Project name</span>
                <input name="name" required maxLength={100} placeholder="isort" />
              </label>
              <label className="platform-field">
                <span>Description</span>
                <textarea
                  name="description"
                  maxLength={500}
                  placeholder="What is this project used for?"
                />
              </label>
              <div className="form-grid">
                <label className="platform-field">
                  <span>Git branch</span>
                  <input name="branch" required defaultValue="main" />
                </label>
                <label className="platform-field">
                  <span>Commit hash</span>
                  <input name="commit" placeholder="9262aa8" maxLength={64} />
                </label>
              </div>
              <label className="platform-field upload-field">
                <span>Python project ZIP</span>
                <input name="archive" type="file" accept=".zip,application/zip" required />
                <small>The archive is uploaded directly to object storage.</small>
              </label>
              {createProject.isError && (
                <div className="auth-error" role="alert">
                  {createProject.error instanceof Error
                    ? createProject.error.message
                    : "Project could not be created."}
                </div>
              )}
              <div className="settings-actions">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => setIsAdding(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="primary-button" disabled={createProject.isPending}>
                  {createProject.isPending ? "Uploadingâ€¦" : "Upload and create"}
                </button>
              </div>
            </form>
          </aside>
        </div>
      )}
    </div>
  );
}
