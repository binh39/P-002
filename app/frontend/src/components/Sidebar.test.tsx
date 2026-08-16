import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import Sidebar from "@/components/Sidebar";

describe("Sidebar", () => {
  it("keeps Docs and Settings beside the user section and navigates correctly", () => {
    const onNavigate = vi.fn();

    render(
      <Sidebar
        currentPage="coverage"
        onNavigate={onNavigate}
        user={{ name: "Demo User", role: "Engineer", photoUrl: null }}
        onSignOut={vi.fn()}
      />,
    );

    const systemNavigation = screen.getByRole("navigation", { name: "System navigation" });
    const docs = screen.getByRole("button", { name: "Docs" });
    const settings = screen.getByRole("button", { name: "Settings" });

    expect(docs).toHaveAttribute("aria-current", "page");
    expect(settings).not.toHaveAttribute("aria-current");
    expect(within(systemNavigation).getAllByRole("button")).toEqual([docs, settings]);
    expect(docs.closest("nav")).toBe(systemNavigation);
    expect(settings.closest("nav")).toBe(systemNavigation);
    expect(systemNavigation.nextElementSibling).toHaveClass("sidebar-user");

    fireEvent.click(docs);
    expect(onNavigate).toHaveBeenCalledWith("coverage");

    fireEvent.click(settings);
    expect(onNavigate).toHaveBeenCalledWith("settings");
  });
});
