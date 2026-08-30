import { ChevronDown, Plus } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { apiRequest } from "@/api/client";
import type { Workspace, WorkspaceList } from "@/domain/workspaces";

export default function WorkspaceSwitcher({ activeId }: { activeId: string }) {
  const [items, setItems] = useState<Workspace[]>([]);
  const [open, setOpen] = useState(false);
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

  const create = async () => {
    const name = window.prompt("Workspace name", `Workspace ${items.length + 1}`)?.trim();
    if (!name) return;
    await apiRequest<Workspace>("/workspaces", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    window.location.assign("/dashboard");
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
        <div className="workspace-menu">
          <button type="button" className="workspace-create" onClick={() => void create()}>
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
                {workspace.name}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
