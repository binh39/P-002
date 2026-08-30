import { Building2, Check, ChevronDown, Plus, X } from "lucide-react";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { apiRequest } from "@/api/client";
import type { Workspace, WorkspaceList } from "@/domain/workspaces";

export default function WorkspaceSwitcher({ activeId }: { activeId: string }) {
  const [items, setItems] = useState<Workspace[]>([]);
  const [open, setOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const root = useRef<HTMLDivElement>(null);
  const active = items.find((item) => item.id === activeId);

  useEffect(() => {
    void apiRequest<WorkspaceList>("/workspaces")
      .then((result) => setItems(result.items))
      .catch(() => setItems([]));
  }, []);
  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);
  useEffect(() => {
    if (!createOpen) return;
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !creating) setCreateOpen(false);
    };
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [createOpen, creating]);

  const showCreate = () => {
    setOpen(false);
    setError(null);
    setName(`Workspace ${items.length + 1}`);
    setCreateOpen(true);
  };
  const create = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedName = name.trim();
    if (!normalizedName) return setError("Enter a workspace name.");
    setCreating(true);
    setError(null);
    try {
      await apiRequest<Workspace>("/workspaces", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: normalizedName }),
      });
      window.location.assign("/dashboard");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Workspace could not be created.");
      setCreating(false);
    }
  };
  const activate = async (workspace: Workspace) => {
    if (workspace.id === activeId) return setOpen(false);
    await apiRequest(`/workspaces/${workspace.id}/activate`, { method: "POST" });
    window.location.reload();
  };

  return (
    <div className="workspace-switcher" ref={root}>
      <button type="button" className="workspace-current" onClick={() => setOpen(!open)}>
        <span title={active?.name}>{active?.name ?? "Workspace 1"}</span>
        <ChevronDown size={15} />
      </button>
      {open && (
        <div className="workspace-menu" aria-label="Workspace menu">
          <div className="workspace-menu-current">
            <span className="workspace-menu-icon">
              <Building2 size={16} />
            </span>
            <span>
              <small>Current workspace</small>
              <strong>{active?.name ?? "Workspace 1"}</strong>
            </span>
          </div>
          <button type="button" className="workspace-create" onClick={showCreate}>
            <Plus size={15} /> Create New Workspace
          </button>
          <div className="workspace-list" role="listbox" aria-label="Workspaces">
            {items.map((workspace) => (
              <button
                type="button"
                key={workspace.id}
                className={workspace.id === activeId ? "is-active" : ""}
                onClick={() => void activate(workspace)}
                title={workspace.name}
              >
                <span>{workspace.name}</span>
                {workspace.id === activeId && <Check size={14} />}
              </button>
            ))}
          </div>
        </div>
      )}
      {createOpen &&
        createPortal(
          <div
            className="modal-backdrop workspace-modal-backdrop"
            role="presentation"
            onMouseDown={() => !creating && setCreateOpen(false)}
          >
            <form
              className="workspace-create-dialog"
              role="dialog"
              aria-modal="true"
              aria-labelledby="create-workspace-title"
              onSubmit={(event) => void create(event)}
              onMouseDown={(event) => event.stopPropagation()}
            >
              <div className="workspace-dialog-header">
                <span className="workspace-dialog-icon">
                  <Building2 size={20} />
                </span>
                <div>
                  <span className="eyebrow">Workspace</span>
                  <h2 id="create-workspace-title">Create new workspace</h2>
                </div>
                <button
                  type="button"
                  className="workspace-dialog-close"
                  aria-label="Close"
                  disabled={creating}
                  onClick={() => setCreateOpen(false)}
                >
                  <X size={17} />
                </button>
              </div>
              <p>
                Give your team a separate space for projects, experiments, prompts and test suites.
              </p>
              <label className="platform-field" htmlFor="new-workspace-name">
                <span>Workspace name</span>
                <input
                  id="new-workspace-name"
                  autoFocus
                  value={name}
                  maxLength={80}
                  disabled={creating}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="e.g. Evaluation team"
                />
                <small>{name.trim().length}/80 characters</small>
              </label>
              {error && (
                <div className="workspace-form-error" role="alert">
                  {error}
                </div>
              )}
              <div className="workspace-dialog-actions">
                <button
                  type="button"
                  className="secondary-button"
                  disabled={creating}
                  onClick={() => setCreateOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="primary-button"
                  disabled={creating || !name.trim()}
                >
                  {creating ? "Creating…" : "Create workspace"}
                </button>
              </div>
            </form>
          </div>,
          document.body,
        )}
    </div>
  );
}
