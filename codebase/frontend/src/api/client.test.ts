import { afterEach, describe, expect, it, vi } from "vitest";

import { apiRequest } from "@/api/client";
import { setTokenProvider } from "@/auth/tokenProvider";

describe("apiRequest", () => {
  afterEach(() => {
    setTokenProvider(async () => null);
    vi.unstubAllGlobals();
  });

  it("adds the current Firebase ID token to connected API requests", async () => {
    setTokenProvider(async () => "firebase-id-token");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiRequest<{ ok: boolean }>("/status")).resolves.toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/status",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer firebase-id-token" }),
      }),
    );
  });
});
