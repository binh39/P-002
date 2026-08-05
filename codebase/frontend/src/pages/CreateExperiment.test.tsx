import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import CreateExperiment from "@/pages/CreateExperiment";

describe("create experiment wizard", () => {
  it("shows the three mock projects and advances through the workflow", () => {
    render(<CreateExperiment />);

    expect(screen.getByRole("heading", { name: "Select Python projects" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /isort/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /httpx/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /attrs/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    expect(screen.getByRole("heading", { name: "Review analyzed functions" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    expect(screen.getByRole("heading", { name: "Configure dataset" })).toBeInTheDocument();
    expect(screen.getAllByText("Highest branch count")).toHaveLength(2);
  });

  it("requires at least one selected project", () => {
    render(<CreateExperiment />);

    fireEvent.click(screen.getByRole("button", { name: /isort/i }));
    fireEvent.click(screen.getByRole("button", { name: /attrs/i }));

    expect(screen.getByRole("button", { name: /continue/i })).toBeDisabled();
  });
});
