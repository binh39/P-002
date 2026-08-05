import { useMemo, useState } from "react";
import { useLocation, useParams } from "wouter";

import { Field, PageHeader, StatCard, StatusBadge } from "@/components/PlatformUI";
import { projectFunctions, pythonProjects, sourcePreview } from "@/mocks/fixtures/platform";

type ProjectTab = "overview" | "functions" | "settings" | "versions";

export default function ProjectDetail() {
  const { projectId = "isort" } = useParams<{ projectId: string }>();
  const [, navigate] = useLocation();
  const [tab, setTab] = useState<ProjectTab>("overview");
  const [sourceName, setSourceName] = useState<string | null>(null);
  const project = pythonProjects.find((item) => item.id === projectId) ?? pythonProjects[0];
  const functions = useMemo(
    () => projectFunctions.filter((item) => item.project === project.id),
    [project.id],
  );

  return (
    <div className="platform-page">
      <button className="back-link" onClick={() => navigate("/projects")}>
        ← All projects
      </button>
      <PageHeader
        eyebrow={`${project.branch} · ${project.commit}`}
        title={project.name}
        description={project.description}
        actions={
          <>
            <button className="secondary-button">Validate</button>
            <button className="primary-button">Re-analyze</button>
          </>
        }
      />

      <div className="platform-tabs" role="tablist">
        {(["overview", "functions", "settings", "versions"] as ProjectTab[]).map((item) => (
          <button key={item} className={tab === item ? "active" : ""} onClick={() => setTab(item)}>
            {item === "settings" ? "Python settings" : item}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <>
          <div className="platform-stats-grid">
            <StatCard
              label="Python files"
              value={project.files}
              detail={`${project.sourceDir} source root`}
            />
            <StatCard
              label="Functions"
              value={project.functions}
              detail="7 warnings excluded"
              tone="violet"
            />
            <StatCard
              label="Statements"
              value={project.statements.toLocaleString()}
              detail="Static executable lines"
              tone="green"
            />
            <StatCard
              label="Branches"
              value={project.branches.toLocaleString()}
              detail="Decision outcomes"
              tone="orange"
            />
          </div>
          <div className="platform-two-column">
            <section className="platform-card">
              <div className="card-heading">
                <div>
                  <h2>Configuration health</h2>
                  <p>Latest validation for this project version.</p>
                </div>
                <StatusBadge tone="success">5/5 checks</StatusBadge>
              </div>
              {[
                "Python 3.11 runtime available",
                "Dependencies installed",
                "Project imports successfully",
                "Pytest discovery succeeded",
                "Branch coverage enabled",
              ].map((check) => (
                <div className="validation-row" key={check}>
                  <span className="validation-check">✓</span>
                  <span>{check}</span>
                  <small>Passed</small>
                </div>
              ))}
            </section>
            <section className="platform-card">
              <div className="card-heading">
                <div>
                  <h2>Project snapshot</h2>
                  <p>Inputs recorded for reproducible runs.</p>
                </div>
              </div>
              <dl className="definition-list">
                <div>
                  <dt>Commit</dt>
                  <dd>{project.commit}</dd>
                </div>
                <div>
                  <dt>Python</dt>
                  <dd>{project.python}</dd>
                </div>
                <div>
                  <dt>Source</dt>
                  <dd>{project.sourceDir}</dd>
                </div>
                <div>
                  <dt>Tests</dt>
                  <dd>{project.testDir}</dd>
                </div>
                <div>
                  <dt>Command</dt>
                  <dd>{project.testCommand}</dd>
                </div>
              </dl>
            </section>
          </div>
        </>
      )}

      {tab === "functions" && (
        <section className="platform-card table-card">
          <div className="table-toolbar">
            <div>
              <h2>Analyzed functions</h2>
              <p>
                {functions.length} shown from {project.functions} functions
              </p>
            </div>
            <div className="toolbar-controls">
              <input placeholder="Search function or file…" />
              <select>
                <option>All statuses</option>
                <option>Valid</option>
                <option>Warning</option>
              </select>
            </div>
          </div>
          <div className="table-scroll">
            <table className="platform-table">
              <thead>
                <tr>
                  <th>File / class</th>
                  <th>Function</th>
                  <th>Lines</th>
                  <th>LOC</th>
                  <th>Statements</th>
                  <th>Branches</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {functions.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <strong>{item.file}</strong>
                      <small>{item.className || "Module function"}</small>
                    </td>
                    <td>
                      <code>{item.name}</code>
                    </td>
                    <td>{item.lines}</td>
                    <td>{item.loc}</td>
                    <td>{item.statements}</td>
                    <td>{item.branches}</td>
                    <td>
                      <StatusBadge tone={item.status === "Valid" ? "success" : "warning"}>
                        {item.status}
                      </StatusBadge>
                    </td>
                    <td>
                      <button className="table-action" onClick={() => setSourceName(item.name)}>
                        View source
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {tab === "settings" && <ProjectSettings project={project} />}

      {tab === "versions" && (
        <section className="platform-card table-card">
          <div className="table-toolbar">
            <div>
              <h2>Project versions</h2>
              <p>Immutable source and configuration snapshots.</p>
            </div>
          </div>
          <table className="platform-table">
            <thead>
              <tr>
                <th>Version</th>
                <th>Branch</th>
                <th>Functions</th>
                <th>Configuration</th>
                <th>Analyzed</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <code>{project.commit}</code>
                </td>
                <td>{project.branch}</td>
                <td>{project.functions}</td>
                <td>cfg-a19c</td>
                <td>{project.analyzedAt}</td>
                <td>
                  <StatusBadge tone="success">Current</StatusBadge>
                </td>
              </tr>
              <tr>
                <td>
                  <code>8a10c4e</code>
                </td>
                <td>{project.branch}</td>
                <td>{project.functions - 7}</td>
                <td>cfg-92bf</td>
                <td>Aug 1, 2026</td>
                <td>
                  <StatusBadge>Archived</StatusBadge>
                </td>
              </tr>
            </tbody>
          </table>
        </section>
      )}

      {sourceName && (
        <div className="drawer-backdrop" onClick={() => setSourceName(null)}>
          <aside className="source-drawer" onClick={(event) => event.stopPropagation()}>
            <div className="drawer-heading">
              <div>
                <span className="eyebrow">
                  {project.name} · {project.sourceDir}
                </span>
                <h2>{sourceName}</h2>
                <p>Lines 34–82 · 31 statements · 12 branches</p>
              </div>
              <button onClick={() => setSourceName(null)}>×</button>
            </div>
            <pre>
              <code>{sourcePreview}</code>
            </pre>
            <div className="drawer-legend">
              <span>
                <i className="covered" />
                Executable statement
              </span>
              <span>
                <i className="branch" />
                Branch point
              </span>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}

function ProjectSettings({ project }: { project: (typeof pythonProjects)[number] }) {
  const [section, setSection] = useState("runtime");
  const sections = ["runtime", "dependencies", "tests", "coverage", "security"];
  return (
    <div className="settings-layout">
      <nav className="settings-nav">
        {sections.map((item) => (
          <button
            key={item}
            className={section === item ? "active" : ""}
            onClick={() => setSection(item)}
          >
            {item}
          </button>
        ))}
      </nav>
      <section className="platform-card settings-panel">
        <div className="card-heading">
          <div>
            <h2>{section[0].toUpperCase() + section.slice(1)} settings</h2>
            <p>Project overrides are versioned with every analysis.</p>
          </div>
          <StatusBadge tone="info">Overrides workspace defaults</StatusBadge>
        </div>
        {section === "runtime" && (
          <div className="form-grid">
            <Field label="Python version">
              <select defaultValue={project.python}>
                <option>3.10</option>
                <option>3.11</option>
                <option>3.12</option>
              </select>
            </Field>
            <Field label="Runtime image">
              <input defaultValue="python:3.11-slim" />
            </Field>
            <Field label="Working directory">
              <input defaultValue="./" />
            </Field>
            <Field label="Source directory">
              <input defaultValue={project.sourceDir} />
            </Field>
            <Field label="CPU">
              <select>
                <option>1 vCPU</option>
                <option>2 vCPU</option>
              </select>
            </Field>
            <Field label="Memory">
              <select>
                <option>2 GiB</option>
                <option>4 GiB</option>
              </select>
            </Field>
          </div>
        )}
        {section === "dependencies" && (
          <div className="form-grid">
            <Field label="Install command">
              <input defaultValue="pip install -r requirements.txt" />
            </Field>
            <Field label="Requirements file">
              <input defaultValue="requirements.txt" />
            </Field>
            <Field label="Lock file">
              <input placeholder="uv.lock / poetry.lock" />
            </Field>
            <Field label="Dependency cache">
              <select>
                <option>Enabled</option>
                <option>Disabled</option>
              </select>
            </Field>
          </div>
        )}
        {section === "tests" && (
          <div className="form-grid">
            <Field label="Framework">
              <select>
                <option>pytest</option>
                <option>unittest</option>
              </select>
            </Field>
            <Field label="Test directory">
              <input defaultValue={project.testDir} />
            </Field>
            <Field label="Test command">
              <input defaultValue={project.testCommand} />
            </Field>
            <Field label="Per-test timeout">
              <input defaultValue="30 seconds" />
            </Field>
            <Field label="Retry count">
              <input defaultValue="1" />
            </Field>
            <Field label="Test pattern">
              <input defaultValue="test_*.py" />
            </Field>
          </div>
        )}
        {section === "coverage" && (
          <div className="form-grid">
            <Field label="Statement coverage">
              <select>
                <option>Enabled</option>
              </select>
            </Field>
            <Field label="Branch coverage">
              <select>
                <option>Enabled</option>
                <option>Disabled</option>
              </select>
            </Field>
            <Field label="Coverage config">
              <input defaultValue=".coveragerc" />
            </Field>
            <Field label="Include pattern">
              <input defaultValue={`${project.sourceDir}**/*.py`} />
            </Field>
            <Field label="Omit pattern">
              <input defaultValue="*/tests/*, */migrations/*" />
            </Field>
            <Field label="Function extraction">
              <select>
                <option>Functions + methods + async</option>
              </select>
            </Field>
          </div>
        )}
        {section === "security" && (
          <div className="form-grid">
            <Field label="Network access">
              <select>
                <option>Disabled during tests</option>
                <option>Allow listed hosts</option>
              </select>
            </Field>
            <Field label="Filesystem">
              <select>
                <option>Read-only source</option>
              </select>
            </Field>
            <Field label="Maximum output">
              <input defaultValue="10 MB" />
            </Field>
            <Field label="Run timeout">
              <input defaultValue="15 minutes" />
            </Field>
            <Field label="Environment variables" hint="Values are resolved from Secret Manager">
              <input defaultValue="PYTHONHASHSEED, TZ" />
            </Field>
            <Field label="Maximum workers">
              <input defaultValue="4" />
            </Field>
          </div>
        )}
        <div className="settings-actions">
          <button className="secondary-button">Reset to workspace defaults</button>
          <button className="secondary-button">Validate configuration</button>
          <button className="primary-button">Save settings</button>
        </div>
      </section>
    </div>
  );
}
