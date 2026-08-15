import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import CoverageGuide from "@/pages/CoverageGuide";

describe("coverage guide", () => {
  it("explains both coverage types and updates the branch example", async () => {
    const user = userEvent.setup();
    render(<CoverageGuide />);

    expect(screen.getByRole("heading", { name: "Statement coverage" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Branch coverage" })).toBeInTheDocument();
    expect(screen.getByText("50%", { selector: ".branch-ring strong" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Both tests" }));

    expect(screen.getByText("100%", { selector: ".branch-ring strong" })).toBeInTheDocument();
    expect(screen.getByText("2 / 2 branches")).toBeInTheDocument();
  });
});
