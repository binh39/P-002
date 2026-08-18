import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { useRepositories } from "@/app/providers";
import { Field, PageHeader } from "@/components/PlatformUI";
import type { AIProvider, ProviderCredential } from "@/domain/providerCredentials";

const tabs = ["General", "AI & Optimization", "Evaluation", "Execution & Security"];
const providerDetails: Array<{ provider: AIProvider; name: string }> = [
  { provider: "gemini", name: "Gemini" },
  { provider: "openai", name: "OpenAI" },
  { provider: "deepseek", name: "DeepSeek" },
];

export default function Settings() {
  const [tab, setTab] = useState(tabs[0]);
  const { providerCredentials } = useRepositories();
  const queryClient = useQueryClient();
  const credentialsQuery = useQuery({
    queryKey: ["provider-credentials"],
    queryFn: ({ signal }) => providerCredentials.list(signal),
  });
  const refreshCredentials = () =>
    queryClient.invalidateQueries({ queryKey: ["provider-credentials"] });

  return (
    <div className="platform-page settings-page">
      <PageHeader eyebrow="Workspace defaults" title="Tool Settings" />
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
              <SettingsSection title="AI provider keys">
                {credentialsQuery.isLoading ? <p>Loading provider credentials…</p> : null}
                {credentialsQuery.isError ? (
                  <p className="form-error">Could not load provider credentials.</p>
                ) : null}
                {providerDetails.map((detail) => (
                  <ProviderKeyForm
                    key={detail.provider}
                    detail={detail}
                    credential={credentialsQuery.data?.find(
                      (item) => item.provider === detail.provider,
                    )}
                    onSave={async (apiKey) => {
                      await providerCredentials.save(detail.provider, apiKey);
                      await refreshCredentials();
                    }}
                    onRemove={async () => {
                      await providerCredentials.remove(detail.provider);
                      await refreshCredentials();
                    }}
                  />
                ))}
              </SettingsSection>
            </>
          )}
          {tab === "AI & Optimization" && <OptimizationSettings />}
          {tab === "Evaluation" && <EvaluationSettings />}
          {tab === "Execution & Security" && <ExecutionSettings />}
        </div>
      </div>
    </div>
  );
}

function ProviderKeyForm({
  detail,
  credential,
  onSave,
  onRemove,
}: {
  detail: { provider: AIProvider; name: string };
  credential?: ProviderCredential;
  onSave(apiKey: string): Promise<void>;
  onRemove(): Promise<void>;
}) {
  const [apiKey, setApiKey] = useState("");
  const save = useMutation({ mutationFn: onSave, onSuccess: () => setApiKey("") });
  const remove = useMutation({ mutationFn: onRemove });
  const error = save.error ?? remove.error;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (apiKey.trim()) save.mutate(apiKey);
  }

  return (
    <form className="integration-row provider-key-row" onSubmit={submit}>
      <div>
        <strong>{detail.name}</strong>
        {credential?.configured ? <span>{credential.maskedKey}</span> : null}
      </div>
      <div className="provider-key-actions">
        <input
          aria-label={`${detail.name} API key`}
          type="password"
          autoComplete="off"
          placeholder={credential?.configured ? "Paste a replacement key" : "Paste API key"}
          value={apiKey}
          onChange={(event) => setApiKey(event.target.value)}
        />
        <button
          className="secondary-button"
          type="submit"
          disabled={!apiKey.trim() || save.isPending}
        >
          {save.isPending ? "Saving…" : credential?.configured ? "Replace" : "Save key"}
        </button>
        {credential?.configured ? (
          <button
            className="text-button danger-button"
            type="button"
            disabled={remove.isPending}
            onClick={() => remove.mutate()}
          >
            {remove.isPending ? "Removing…" : "Remove"}
          </button>
        ) : null}
      </div>
      {error ? <p className="form-error">{error.message}</p> : null}
    </form>
  );
}

function OptimizationSettings() {
  return (
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
  );
}

function EvaluationSettings() {
  return (
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
  );
}

function ExecutionSettings() {
  return (
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
  );
}

function SettingsSection({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="platform-card settings-panel">
      <div className="card-heading">
        <div>
          <h2>{title}</h2>
          {description ? <p>{description}</p> : null}
        </div>
      </div>
      {children}
    </section>
  );
}
