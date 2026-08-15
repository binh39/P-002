import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import App from "@/App";

describe("application routing", () => {
  beforeEach(() => {
    sessionStorage.clear();
    window.history.replaceState(null, "", "/dashboard");
  });

  afterEach(() => {
    sessionStorage.clear();
  });

  it("protects application routes and enters the demo workspace", async () => {
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Login" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Continue with demo account" }));

    expect(await screen.findByText("hybrid data")).toBeInTheDocument();
    expect(screen.getByRole("navigation")).toBeInTheDocument();
    expect(window.location.pathname).toBe("/dashboard");
  });
});
