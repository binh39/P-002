import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import WorkspaceSwitcher from "@/components/WorkspaceSwitcher";

describe("WorkspaceSwitcher", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("opens a solid workspace menu and uses an in-app create dialog", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          active_workspace_id: "workspace-1",
          items: [
            {
              id: "workspace-1",
              name: "Evaluation Team",
              owner_id: "user-1",
              members: [],
              created_at: "2026-01-01T00:00:00Z",
              updated_at: "2026-01-01T00:00:00Z",
            },
          ],
        }),
      }),
    );

    render(<WorkspaceSwitcher activeId="workspace-1" />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /Evaluation Team/i })).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByRole("button", { name: /Evaluation Team/i }));

    expect(screen.getByLabelText("Workspace menu")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Create New Workspace" }));

    const dialog = screen.getByRole("dialog", { name: "Create new workspace" });
    expect(dialog).toBeInTheDocument();
    expect(screen.getByLabelText(/Workspace name/)).toHaveValue("Workspace 2");
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(dialog).not.toBeInTheDocument();
  });
});
