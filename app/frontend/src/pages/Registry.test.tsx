import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Registry from "@/pages/Registry";

describe("Registry", () => {
  it("uses the shared page layout and stable table columns", () => {
    const { container } = render(<Registry />);

    expect(container.firstElementChild).toHaveClass("platform-page", "registry-page");
    expect(screen.getByRole("heading", { name: "Prompt Registry" })).toBeInTheDocument();
    expect(screen.getByRole("table")).toHaveClass("registry-table");
    expect(screen.getByText("PRG-031")).toHaveClass("registry-id-cell");
  });
});
