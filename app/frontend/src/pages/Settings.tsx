import { useState } from "react";

import { Field, PageHeader, StatusBadge } from "@/components/PlatformUI";

const tabs = ["General", "AI & Optimization", "Evaluation", "Execution & Security"];

export default function Settings() {
  const [tab, setTab] = useState(tabs[0]);
  return (
    <div className="platform-page">
      <PageHeader
        eyebrow="Workspace defaults"
        title="Tool Settings"
        description="Global defaults inherited by projects and experiments."
        actions={<button className="primary-button">Save changes</button>}
      />
      <div className="settings-layout tool-settings-layout">
        <nav className="settings-nav">
          {tabs.map((item) => (
            <button
              key={item}
              className={tab === item ? "active" : ""}
              onClick={() => setTab(item)}
            >
              {item}
            </button>
          ))}
        </nav>
        <div className="settings-stack">
          {tab === "General" && (
            <>
              <SettingsSection
                title="Workspace"
                description="Naming, locale and retention defaults."
              >
                <div className="form-grid">
                  <Field label="Workspace name">
                    <input defaultValue="PromptOpt Research" />
                  </Field>
                  <Field label="Timezone">
                    <select>
                      <option>Asia/Ho_Chi_Minh</option>
                      <option>UTC</option>
                    </select>
                  </Field>
                  <Field label="Metric precision">
                    <select>
                      <option>2 decimal places</option>
                      <option>3 decimal places</option>
                    </select>
                  </Field>
                  <Field label="Default export">
                    <select>
                      <option>Markdown</option>
                      <option>CSV</option>
                      <option>JSON</option>
                    </select>
                  </Field>
                  <Field label="Experiment retention">
                    <select>
                      <option>180 days</option>
                      <option>365 days</option>
                    </select>
                  </Field>
                  <Field label="Log retention">
                    <select>
                      <option>30 days</option>
                      <option>90 days</option>
                    </select>
                  </Field>
                </div>
              </SettingsSection>
              <SettingsSection
                title="Cloud resources"
                description="Read-only deployment context; credentials stay in Google Secret Manager."
              >
                <div className="integration-row">
                  <div>
                    <strong>Google Cloud</strong>
                    <span>Project project-7df9f963-9fe0-4b76-b3d · asia-southeast1</span>
                  </div>
                  <StatusBadge tone="success">Connected</StatusBadge>
                </div>
                <div className="integration-row">
                  <div>
                    <strong>Cloud Storage</strong>
                    <span>promptopt-projects · Standard</span>
                  </div>
                  <StatusBadge tone="success">Healthy</StatusBadge>
                </div>
                <div className="integration-row">
                  <div>
                    <strong>Firestore</strong>
                    <span>Native mode · nam5</span>
                  </div>
                  <StatusBadge tone="info">Planned</StatusBadge>
                </div>
              </SettingsSection>
            </>
          )}
          {tab === "AI & Optimization" && (
            <>
              <SettingsSection
                title="Gemini provider"
                description="Secret values are never returned to the browser."
              >
                <div className="integration-row">
                  <div>
                    <strong>Gemini API</strong>
                    <span>Secret: gemini-api-key · Last validated 4 minutes ago</span>
                  </div>
                  <StatusBadge tone="success">Connected</StatusBadge>
                </div>
                <div className="form-grid">
                  <Field label="Default model">
                    <select>
                      <option>Gemini 2.5 Pro</option>
                      <option>Gemini 2.5 Flash</option>
                    </select>
                  </Field>
                  <Field label="Fallback model">
                    <select>
                      <option>Gemini 2.5 Flash</option>
                    </select>
                  </Field>
                  <Field label="Temperature">
                    <input defaultValue="0.3" />
                  </Field>
                  <Field label="Max output tokens">
                    <input defaultValue="4096" />
                  </Field>
                </div>
              </SettingsSection>
              <SettingsSection
                title="Optimization defaults"
                description="Experiments may override these values."
              >
                <div className="form-grid">
                  <Field label="Optimizer">
                    <select>
                      <option>GEPA</option>
                      <option>DSPy MIPROv2</option>
                    </select>
                  </Field>
                  <Field label="Iterations">
                    <input defaultValue="10" />
                  </Field>
                  <Field label="Candidates / iteration">
                    <input defaultValue="4" />
                  </Field>
                  <Field label="Stop patience">
                    <input defaultValue="3" />
                  </Field>
                  <Field label="Default cost budget">
                    <input defaultValue="$12.00" />
                  </Field>
                  <Field label="Optimization timeout">
                    <input defaultValue="90 minutes" />
                  </Field>
                </div>
              </SettingsSection>
            </>
          )}
          {tab === "Evaluation" && (
            <>
              <SettingsSection
                title="Scoring formula"
                description="Weights must total 1.00 and apply equally to baseline and optimized prompts."
              >
                <div className="weight-row">
                  <span>Branch coverage</span>
                  <input defaultValue="0.50" />
                  <b>50%</b>
                </div>
                <div className="weight-row">
                  <span>Statement coverage</span>
                  <input defaultValue="0.30" />
                  <b>30%</b>
                </div>
                <div className="weight-row">
                  <span>Test pass rate</span>
                  <input defaultValue="0.20" />
                  <b>20%</b>
                </div>
                <div className="formula-preview">
                  Score = 0.50 × Branch + 0.30 × Statement + 0.20 × Pass rate
                </div>
              </SettingsSection>
              <SettingsSection
                title="Failure handling"
                description="Consistent penalties protect result comparability."
              >
                <div className="form-grid">
                  <Field label="Test failure penalty">
                    <input defaultValue="-0.10" />
                  </Field>
                  <Field label="Timeout penalty">
                    <input defaultValue="-0.15" />
                  </Field>
                  <Field label="Coverage error score">
                    <input defaultValue="0.00" />
                  </Field>
                  <Field label="Target branch coverage">
                    <input defaultValue="85%" />
                  </Field>
                  <Field label="Target statement coverage">
                    <input defaultValue="90%" />
                  </Field>
                  <Field label="Best prompt rule">
                    <select>
                      <option>Highest validation score</option>
                    </select>
                  </Field>
                </div>
              </SettingsSection>
            </>
          )}
          {tab === "Execution & Security" && (
            <>
              <SettingsSection
                title="Execution defaults"
                description="Project settings can request lower limits, never exceed workspace maximums."
              >
                <div className="form-grid">
                  <Field label="Parallel workers">
                    <input defaultValue="4" />
                  </Field>
                  <Field label="Function timeout">
                    <input defaultValue="120 seconds" />
                  </Field>
                  <Field label="Run timeout">
                    <input defaultValue="90 minutes" />
                  </Field>
                  <Field label="Retry count">
                    <input defaultValue="1" />
                  </Field>
                  <Field label="CPU limit">
                    <select>
                      <option>2 vCPU</option>
                    </select>
                  </Field>
                  <Field label="Memory limit">
                    <select>
                      <option>4 GiB</option>
                    </select>
                  </Field>
                </div>
              </SettingsSection>
              <SettingsSection
                title="Sandbox policy"
                description="Uploaded code executes in isolated jobs, never inside the API service."
              >
                <div className="toggle-row">
                  <div>
                    <strong>Disable outbound network</strong>
                    <span>Block package and application traffic during evaluation</span>
                  </div>
                  <input type="checkbox" defaultChecked />
                </div>
                <div className="toggle-row">
                  <div>
                    <strong>Read-only source filesystem</strong>
                    <span>Only temporary test and report paths are writable</span>
                  </div>
                  <input type="checkbox" defaultChecked />
                </div>
                <div className="form-grid">
                  <Field label="Maximum upload">
                    <input defaultValue="50 MB" />
                  </Field>
                  <Field label="Maximum logs">
                    <input defaultValue="10 MB" />
                  </Field>
                  <Field label="Allowed environment names">
                    <input defaultValue="PYTHONHASHSEED, TZ, LANG" />
                  </Field>
                  <Field label="Secret source">
                    <select>
                      <option>Google Secret Manager</option>
                    </select>
                  </Field>
                </div>
              </SettingsSection>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function SettingsSection({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <section className="platform-card settings-panel">
      <div className="card-heading">
        <div>
          <h2>{title}</h2>
          <p>{description}</p>
        </div>
      </div>
      {children}
    </section>
  );
}
