import { useQuery } from "@tanstack/react-query";
import { useLocation } from "wouter";

import { useRepositories } from "@/app/providers";
import { PageHeader, StatCard, StatusBadge } from "@/components/PlatformUI";

export default function Projects() {
  const [, navigate] = useLocation();
  const { projects } = useRepositories();
  const query = useQuery({
    queryKey: ["sample-projects"],
    queryFn: ({ signal }) => projects.listSamples(signal),
  });

  if (query.isPending) {
    return (
      <div className="page-state" role="status">
        Loading sample projects…
      </div>
    );
  }
  if (query.isError) {
    return (
      <div className="page-state page-state-error" role="alert">
        <h2>Sample projects are unavailable</h2>
        <p>
          {query.error instanceof Error ? query.error.message : "An unexpected error occurred."}
        </p>
        <button onClick={() => query.refetch()}>Try again</button>
      </div>
    );
  }

  const pythonProjects = query.data;
  const totalFunctions = pythonProjects.reduce((sum, project) => sum + project.functions, 0);

  return (
    <div className="platform-page">
      <PageHeader
        eyebrow="Experiment fixtures"
        title="Sample Python Projects"
        description="Run experiments against four immutable repositories without uploading source."
        actions={
          <button
            className="primary-button"
            type="button"
            disabled
            title="Project import is coming soon"
            aria-label="Create project (coming soon)"
          >
            + Create project
          </button>
        }
      />

      <div className="platform-stats-grid">
        <StatCard label="Projects" value={pythonProjects.length} detail="Pinned snapshots" />
        <StatCard
          label="Python files"
          value={pythonProjects.reduce((sum, project) => sum + project.files, 0)}
          detail="Bundled with the API"
          tone="violet"
        />
        <StatCard
          label="Functions"
          value={totalFunctions}
          detail="Analyzed in memory with AST"
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
        <div className="empty-state">The bundled sample catalog is unavailable.</div>
      ) : (
        <div className="project-grid">
          {pythonProjects.map((project) => (
            <article className="project-card" key={project.id}>
              <div className="project-card-top">
                <div className="project-symbol">{project.name.slice(0, 2).toUpperCase()}</div>
                <StatusBadge tone={project.status === "ready" ? "success" : "warning"}>
                  {project.status === "ready" ? "Ready" : "Needs attention"}
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
                <span>Read-only sample</span>
                <button onClick={() => navigate(`/projects/${project.id}`)}>Open project →</button>
              </div>
            </article>
          ))}
        </div>
      )}

      <div className="platform-callout">
        <div>
          <strong>No project upload is required</strong>
          <p>
            isort, mimesis, mlxtend and typesystem are pinned snapshots. Experiments and runs are
            saved, but these projects and their analyzed functions are not written to Firestore.
          </p>
        </div>
        <button className="secondary-button" onClick={() => navigate("/experiments/new")}>
          Start with a sample
        </button>
      </div>
    </div>
  );
}
