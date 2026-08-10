import { useState } from "react";

import { PageHeader, StatusBadge } from "@/components/PlatformUI";
import { datasets, projectFunctions } from "@/mocks/fixtures/platform";

export default function Datasets() {
  const [selected, setSelected] = useState(datasets[0]);
  return (
    <div className="platform-page">
      <PageHeader
        eyebrow="Reproducible evaluation"
        title="Datasets"
        description="Immutable train, validation and test snapshots used by experiments."
        actions={<button className="primary-button">+ Build dataset</button>}
      />
      <div className="platform-two-column dataset-layout">
        <section className="platform-card dataset-list">
          <div className="card-heading">
            <div>
              <h2>Dataset snapshots</h2>
              <p>{datasets.length} reusable snapshots</p>
            </div>
          </div>
          {datasets.map((dataset) => (
            <button
              key={dataset.id}
              className={selected.id === dataset.id ? "dataset-item active" : "dataset-item"}
              onClick={() => setSelected(dataset)}
            >
              <div>
                <strong>{dataset.name}</strong>
                <span>
                  {dataset.id} · {dataset.projects}
                </span>
              </div>
              <StatusBadge tone={dataset.status === "In use" ? "info" : "success"}>
                {dataset.status}
              </StatusBadge>
              <div className="dataset-counts">
                <span>
                  Train <b>{dataset.train}</b>
                </span>
                <span>
                  Val <b>{dataset.validation}</b>
                </span>
                <span>
                  Test <b>{dataset.test}</b>
                </span>
              </div>
            </button>
          ))}
        </section>
        <div>
          <section className="platform-card dataset-detail">
            <div className="card-heading">
              <div>
                <span className="eyebrow">{selected.id}</span>
                <h2>{selected.name}</h2>
                <p>
                  {selected.method} · Seed {selected.seed}
                </p>
              </div>
              <button className="secondary-button">Use in experiment</button>
            </div>
            <div className="dataset-bar">
              <span
                style={{
                  width: `${(selected.train / (selected.train + selected.validation + selected.test)) * 100}%`,
                }}
              >
                Train
              </span>
              <span
                style={{
                  width: `${(selected.validation / (selected.train + selected.validation + selected.test)) * 100}%`,
                }}
              >
                Validation
              </span>
              <span
                style={{
                  width: `${(selected.test / (selected.train + selected.validation + selected.test)) * 100}%`,
                }}
              >
                Test
              </span>
            </div>
            <div className="dataset-metrics">
              <div>
                <span>Functions</span>
                <strong>{selected.train + selected.validation + selected.test}</strong>
              </div>
              <div>
                <span>Statements</span>
                <strong>3,184</strong>
              </div>
              <div>
                <span>Branches</span>
                <strong>892</strong>
              </div>
              <div>
                <span>Created</span>
                <strong>{selected.created}</strong>
              </div>
            </div>
          </section>
          <section className="platform-card table-card">
            <div className="table-toolbar">
              <div>
                <h2>Test set preview</h2>
                <p>Locked evaluation functions · never used for optimization</p>
              </div>
              <StatusBadge tone="success">✓ Isolated</StatusBadge>
            </div>
            <div className="table-scroll">
              <table className="platform-table">
                <thead>
                  <tr>
                    <th>Project</th>
                    <th>Function</th>
                    <th>File</th>
                    <th>Statements</th>
                    <th>Branches</th>
                  </tr>
                </thead>
                <tbody>
                  {projectFunctions.slice(0, 5).map((item) => (
                    <tr key={item.id}>
                      <td>{item.project}</td>
                      <td>
                        <code>{item.name}</code>
                      </td>
                      <td>{item.file}</td>
                      <td>{item.statements}</td>
                      <td>{item.branches}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
