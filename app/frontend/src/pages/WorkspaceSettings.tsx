import { useEffect, useState } from "react";

import { apiRequest } from "@/api/client";
import { useAuth } from "@/auth/AuthProvider";
import type { Workspace, WorkspaceList } from "@/domain/workspaces";

export default function WorkspaceSettings() {
  const { user } = useAuth();
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const isOwner = workspace?.owner_id === user?.id;

  useEffect(() => {
    void apiRequest<WorkspaceList>("/workspaces").then((result) => {
      const active = result.items.find((item) => item.id === result.active_workspace_id) ?? null;
      setWorkspace(active);
      setName(active?.name ?? "");
    });
  }, []);

  const update = async (path: string, init: RequestInit) => {
    if (!workspace) return;
    setError(null);
    try {
      setWorkspace(await apiRequest<Workspace>(path, init));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Workspace update failed");
    }
  };

  if (!workspace) return <div className="page-state">Loading workspace settings…</div>;
  return (
    <section className="settings-page workspace-settings-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Workspace</p>
          <h1>Workspace Settings</h1>
        </div>
      </header>
      {error && (
        <div className="page-error" role="alert">
          {error}
        </div>
      )}
      <div className="settings-card">
        <h2>General</h2>
        <label className="settings-field">
          <span>Workspace name</span>
          <div className="workspace-inline-form">
            <input
              value={name}
              maxLength={80}
              disabled={!isOwner}
              onChange={(event) => setName(event.target.value)}
            />
            {isOwner && (
              <button
                type="button"
                onClick={() =>
                  void update(`/workspaces/${workspace.id}`, {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name }),
                  })
                }
              >
                Save
              </button>
            )}
          </div>
        </label>
      </div>
      <div className="settings-card">
        <h2>Members</h2>
        {isOwner && (
          <div className="workspace-inline-form">
            <input
              type="email"
              value={email}
              placeholder="member@company.com"
              onChange={(event) => setEmail(event.target.value)}
            />
            <button
              type="button"
              onClick={() =>
                void update(`/workspaces/${workspace.id}/members`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ email }),
                }).then(() => setEmail(""))
              }
            >
              Add member
            </button>
          </div>
        )}
        <div className="workspace-members">
          {workspace.members.map((member) => (
            <div className="workspace-member" key={member.user_id}>
              <div>
                <strong>{member.name}</strong>
                <small>
                  {member.email ?? "No email"} ·{" "}
                  {member.role === "prompt_reviewer" ? "Reviewer" : "Prompt Engineer"}
                </small>
              </div>
              {isOwner && member.user_id !== workspace.owner_id && (
                <button
                  type="button"
                  onClick={() =>
                    void update(`/workspaces/${workspace.id}/members/${member.user_id}`, {
                      method: "DELETE",
                    })
                  }
                >
                  Remove
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
