import { useLocation } from "wouter";

import { PageHeader, StatCard, StatusBadge } from "@/components/PlatformUI";
import { pythonProjects } from "@/mocks/fixtures/platform";

export default function Projects() {
  const [, navigate] = useLocation();
  const totalFunctions = pythonProjects.reduce((sum, project) => sum + project.functions, 0);

  return (
    <div className="platform-page">
      <PageHeader
        eyebrow="Code inventory"
        title="Python Projects"
        description="Manage source versions, runtime configuration and function analysis."
        actions={<button className="primary-button">+ Add project</button>}
      />

      <div className="platform-stats-grid">
        <StatCard label="Projects" value={pythonProjects.length} detail="2 ready · 1 warning" />
        <StatCard label="Python files" value="140" detail="Across all versions" tone="violet" />
        <StatCard
          label="Functions"
          value={totalFunctions}
          detail="Analyzed with Python AST"
          tone="green"
        />
        <StatCard label="Branches" value="3,800" detail="Coverage candidates" tone="orange" />
      </div>

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
              <span>Analyzed {project.analyzedAt}</span>
              <button onClick={() => navigate(`/projects/${project.id}`)}>Open project →</button>
            </div>
          </article>
        ))}
      </div>

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
    </div>
  );
}
