import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import Sidebar from "@/components/Sidebar";

describe("Sidebar", () => {
  it("keeps Settings beside the user section and navigates correctly", () => {
    const onNavigate = vi.fn();

    render(
      <Sidebar
        currentPage="settings"
        onNavigate={onNavigate}
        user={{ name: "Demo User", role: "Engineer", photoUrl: null }}
        onSignOut={vi.fn()}
      />,
    );

    const systemNavigation = screen.getByRole("navigation", { name: "System navigation" });
    const settings = screen.getByRole("button", { name: "Settings" });

    expect(settings).toHaveAttribute("aria-current", "page");
    expect(settings.closest("nav")).toBe(systemNavigation);
    expect(systemNavigation.nextElementSibling).toHaveClass("sidebar-user");

    fireEvent.click(settings);
    expect(onNavigate).toHaveBeenCalledWith("settings");
  });
});
