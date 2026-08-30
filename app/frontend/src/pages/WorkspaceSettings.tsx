import { Building2, Crown, Mail, Save, ShieldCheck, Trash2, UserPlus, Users } from "lucide-react";
import { type FormEvent, type ReactNode, useEffect, useState } from "react";

import { apiRequest } from "@/api/client";
import { useAuth } from "@/auth/AuthProvider";
import { PageHeader } from "@/components/PlatformUI";
import type { Workspace, WorkspaceList } from "@/domain/workspaces";

export default function WorkspaceSettings() {
  const { user } = useAuth();
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<string | null>(null);
  const isOwner = workspace?.owner_id === user?.id;

  useEffect(() => {
    void apiRequest<WorkspaceList>("/workspaces")
      .then((result) => {
        const active = result.items.find((item) => item.id === result.active_workspace_id) ?? null;
        setWorkspace(active);
        setName(active?.name ?? "");
      })
      .catch((reason) =>
        setError(reason instanceof Error ? reason.message : "Workspace could not be loaded"),
      );
  }, []);

  const update = async (action: string, path: string, init: RequestInit) => {
    if (!workspace) return false;
    setError(null);
    setPending(action);
    try {
      setWorkspace(await apiRequest<Workspace>(path, init));
      return true;
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Workspace update failed");
      return false;
    } finally {
      setPending(null);
    }
  };

  const addMember = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedEmail = email.trim();
    if (!normalizedEmail || !workspace) return;
    const saved = await update("add-member", `/workspaces/${workspace.id}/members`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: normalizedEmail }),
    });
    if (saved) setEmail("");
  };

  if (!workspace) {
    return error ? (
      <div className="page-state page-error" role="alert">
        {error}
      </div>
    ) : (
      <div className="page-state">Loading workspace settings…</div>
    );
  }

  return (
    <section className="platform-page workspace-settings-page">
      <PageHeader title="Workspace Settings" />
      {error && (
        <div className="platform-callout workspace-settings-error" role="alert">
          {error}
        </div>
      )}
      <div className="workspace-settings-grid">
        <div className="platform-card workspace-overview-card">
          <SectionHeading icon={<Building2 size={20} />} title="Workspace profile" description="" />
          <div className="workspace-profile-summary">
            <span className="workspace-profile-mark">
              {workspace.name.slice(0, 1).toUpperCase()}
            </span>
            <div>
              <strong>{workspace.name}</strong>
              <small>
                {workspace.members.length} {workspace.members.length === 1 ? "member" : "members"}
              </small>
            </div>
            {isOwner && (
              <span className="workspace-owner-badge">
                <Crown size={13} /> Owner
              </span>
            )}
          </div>
          <label className="platform-field workspace-name-field">
            <span>Workspace name</span>
            <div className="workspace-inline-form">
              <input
                value={name}
                maxLength={80}
                disabled={!isOwner || pending !== null}
                onChange={(event) => setName(event.target.value)}
              />
              {isOwner && (
                <button
                  className="primary-button"
                  type="button"
                  disabled={pending !== null || !name.trim() || name.trim() === workspace.name}
                  onClick={() =>
                    void update("rename", `/workspaces/${workspace.id}`, {
                      method: "PATCH",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ name: name.trim() }),
                    })
                  }
                >
                  <Save size={15} /> {pending === "rename" ? "Saving…" : "Save changes"}
                </button>
              )}
            </div>
          </label>
        </div>

        <div className="platform-card workspace-members-card">
          <SectionHeading icon={<Users size={20} />} title="Workspace members" description="" />
          {isOwner && (
            <form className="workspace-add-member" onSubmit={(event) => void addMember(event)}>
              <label className="platform-field">
                <span className="sr-only">Add member by email</span>
                <div className="workspace-inline-form">
                  <span className="workspace-email-input">
                    <Mail size={16} />
                    <input
                      type="email"
                      value={email}
                      placeholder="member@company.com"
                      disabled={pending !== null}
                      onChange={(event) => setEmail(event.target.value)}
                    />
                  </span>
                  <button
                    className="secondary-button"
                    type="submit"
                    disabled={pending !== null || !email.trim()}
                  >
                    <UserPlus size={15} /> {pending === "add-member" ? "Adding…" : "Add member"}
                  </button>
                </div>
                <small>The person must already have a PromptOpt account.</small>
              </label>
            </form>
          )}
          <div className="workspace-member-list">
            {workspace.members.map((member) => (
              <div className="workspace-member" key={member.user_id}>
                <span className="workspace-member-avatar">{initials(member.name)}</span>
                <div className="workspace-member-copy">
                  <strong>{member.name}</strong>
                  <small>{member.email ?? "No email address"}</small>
                </div>
                <span className="workspace-role-badge">
                  <ShieldCheck size={13} />
                  {member.role === "prompt_reviewer" ? "Reviewer" : "Prompt Engineer"}
                </span>
                {member.user_id === workspace.owner_id && (
                  <span className="workspace-owner-label">
                    <Crown size={13} /> Owner
                  </span>
                )}
                {isOwner && member.user_id !== workspace.owner_id && (
                  <button
                    className="workspace-remove-member"
                    type="button"
                    aria-label={`Remove ${member.name}`}
                    disabled={pending !== null}
                    onClick={() =>
                      void update(
                        `remove-${member.user_id}`,
                        `/workspaces/${workspace.id}/members/${member.user_id}`,
                        { method: "DELETE" },
                      )
                    }
                  >
                    <Trash2 size={15} />
                    <span>{pending === `remove-${member.user_id}` ? "Removing…" : "Remove"}</span>
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function SectionHeading({
  icon,
  kicker,
  title,
  description,
}: {
  icon: ReactNode;
  kicker?: string;
  title: string;
  description: string;
}) {
  return (
    <div className="workspace-settings-heading">
      <span className="workspace-settings-icon">{icon}</span>
      <div>
        {kicker && <span className="card-kicker">{kicker}</span>}
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>
    </div>
  );
}

function initials(name: string) {
  return name
    .split(" ")
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}
