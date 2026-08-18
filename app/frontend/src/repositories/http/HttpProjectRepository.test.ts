import { afterEach, describe, expect, it, vi } from "vitest";

import { setTokenProvider } from "@/auth/tokenProvider";
import { HttpProjectRepository } from "@/repositories/http/HttpProjectRepository";

function projectResponse() {
  return {
    id: "project-1",
    name: "payments",
    description: "",
    branch: "main",
    commit: null,
    status: "analyzing",
    settings: {
      runtime: { python_version: "3.11", source_directory: "src" },
      tests: { test_directory: "tests", test_command: "pytest -q" },
    },
    python_file_count: 0,
    function_count: 0,
    statement_count: 0,
    branch_count: 0,
    analyzed_at: null,
  };
}

describe("HttpProjectRepository", () => {
  afterEach(() => {
    setTokenProvider(async () => null);
    vi.unstubAllGlobals();
  });

  it("uploads an unknown browser ZIP MIME type and queues static analysis", async () => {
    const responses = [
      new Response(
        JSON.stringify({
          id: "upload-1",
          upload_url: "https://storage.example/upload",
          method: "PUT",
          headers: { "Content-Type": "application/zip" },
        }),
        { status: 201, headers: { "Content-Type": "application/json" } },
      ),
      new Response(null, { status: 200 }),
      new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }),
      new Response(JSON.stringify(projectResponse()), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
      new Response(JSON.stringify(projectResponse()), {
        status: 202,
        headers: { "Content-Type": "application/json" },
      }),
    ];
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(responses.shift()));
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["PK"], "payments.zip", { type: "application/octet-stream" });

    const result = await new HttpProjectRepository().create({
      name: "payments",
      description: "",
      branch: "main",
      file,
    });

    expect(result.status).toBe("analyzing");
    expect(JSON.parse(fetchMock.mock.calls[0][1].body as string)).toMatchObject({
      filename: "payments.zip",
      content_type: "application/zip",
      size_bytes: file.size,
    });
    expect(fetchMock.mock.calls[1]).toEqual([
      "https://storage.example/upload",
      expect.objectContaining({
        method: "PUT",
        headers: { "Content-Type": "application/zip" },
        body: file,
      }),
    ]);
    expect(fetchMock).toHaveBeenCalledTimes(5);
  });
});
