import { useLocation } from "wouter";

import { PageHeader, StatCard, StatusBadge } from "@/components/PlatformUI";
import { experiments } from "@/mocks/fixtures/platform";

const toneByStatus = {
  Running: "info",
  Completed: "success",
  Failed: "danger",
  Draft: "neutral",
} as const;

export default function Experiments() {
  const [, navigate] = useLocation();
  return (
    <div className="platform-page">
      <PageHeader
        eyebrow="Evaluation workspace"
        title="Experiments"
        description="Configure, run and compare prompt optimization experiments."
        actions={
          <button className="primary-button" onClick={() => navigate("/experiments/new")}>
            + Create experiment
          </button>
        }
      />
      <div className="platform-stats-grid">
        <StatCard label="Total experiments" value="24" detail="4 this week" />
        <StatCard label="Running" value="1" detail="64 / 120 functions" tone="violet" />
        <StatCard label="Best score" value="0.82" detail="+0.16 over baseline" tone="green" />
        <StatCard label="Failed runs" value="2" detail="8.3% failure rate" tone="orange" />
      </div>
      <section className="platform-card table-card">
        <div className="table-toolbar">
          <div>
            <h2>All experiments</h2>
            <p>Draft, active and completed evaluations.</p>
          </div>
          <div className="toolbar-controls">
            <input placeholder="Search experiments…" />
            <select>
              <option>All statuses</option>
              <option>Running</option>
              <option>Completed</option>
              <option>Draft</option>
            </select>
          </div>
        </div>
        <div className="table-scroll">
          <table className="platform-table">
            <thead>
              <tr>
                <th>Experiment</th>
                <th>Projects / Dataset</th>
                <th>Model</th>
                <th>Status</th>
                <th>Score</th>
                <th>Statement</th>
                <th>Branch</th>
                <th>Updated</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {experiments.map((item) => (
                <tr key={item.id}>
                  <td>
                    <strong>{item.name}</strong>
                    <small>{item.id}</small>
                  </td>
                  <td>
                    <strong>{item.projects}</strong>
                    <small>{item.dataset}</small>
                  </td>
                  <td>{item.model}</td>
                  <td>
                    <StatusBadge tone={toneByStatus[item.status as keyof typeof toneByStatus]}>
                      {item.status}
                    </StatusBadge>
                  </td>
                  <td>
                    <strong>{item.score}</strong>
                  </td>
                  <td>{item.statement}</td>
                  <td>{item.branch}</td>
                  <td>{item.updated}</td>
                  <td>
                    <button
                      className="table-action"
                      onClick={() =>
                        navigate(
                          item.status === "Completed"
                            ? `/runs/${item.id}/compare`
                            : `/runs/${item.id}`,
                        )
                      }
                    >
                      {item.status === "Completed" ? "Results" : "Open"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
