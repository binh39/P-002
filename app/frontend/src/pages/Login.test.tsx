import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import Login from "@/pages/Login";

function createProps() {
  return {
    onClearError: vi.fn(),
    onGoogleSignIn: vi.fn().mockResolvedValue(undefined),
    onEmailSignIn: vi.fn().mockResolvedValue(undefined),
    onRegister: vi.fn().mockResolvedValue(undefined),
    onPasswordReset: vi.fn().mockResolvedValue(undefined),
    connected: true,
    authError: null,
  };
}

describe("Login", () => {
  it("prefills and signs in with the demo account", async () => {
    const user = userEvent.setup();
    const props = createProps();
    render(<Login {...props} />);

    expect(screen.getByRole("heading", { name: "Login" })).toBeInTheDocument();
    expect(screen.getByLabelText("Email address")).toHaveValue("admin@gmail.com");
    expect(screen.getByLabelText("Password")).toHaveValue("88888888");
    await user.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() =>
      expect(props.onEmailSignIn).toHaveBeenCalledWith("admin@gmail.com", "88888888"),
    );
  });

  it("switches to registration and validates matching passwords", async () => {
    const user = userEvent.setup();
    const props = createProps();
    render(<Login {...props} />);

    await user.click(screen.getByRole("button", { name: "Create new account" }));
    expect(screen.getByRole("heading", { name: "Register" })).toBeInTheDocument();

    await user.type(screen.getByLabelText("Full name"), "Alex Morgan");
    await user.clear(screen.getByLabelText("Email address"));
    await user.type(screen.getByLabelText("Email address"), "alex@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.type(screen.getByLabelText("Confirm password"), "different123");
    await user.click(screen.getByRole("button", { name: "Register" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Passwords do not match.");
    expect(props.onRegister).not.toHaveBeenCalled();

    await user.clear(screen.getByLabelText("Confirm password"));
    await user.type(screen.getByLabelText("Confirm password"), "password123");
    await user.click(screen.getByRole("button", { name: "Register" }));

    await waitFor(() =>
      expect(props.onRegister).toHaveBeenCalledWith(
        "Alex Morgan",
        "alex@example.com",
        "password123",
        "prompt_engineer",
      ),
    );
  });

  it("sends a password reset and keeps the legal text on one line", async () => {
    const user = userEvent.setup();
    const props = createProps();
    render(<Login {...props} />);

    await user.clear(screen.getByLabelText("Email address"));
    await user.type(screen.getByLabelText("Email address"), "alex@example.com");
    await user.click(screen.getByRole("button", { name: "Forgot password?" }));

    expect(
      await screen.findByText("Password reset instructions have been sent to your email."),
    ).toBeInTheDocument();
    expect(props.onPasswordReset).toHaveBeenCalledWith("alex@example.com");
    expect(screen.getByText(/By signing in/)).toHaveClass("auth-legal");
  });
});
