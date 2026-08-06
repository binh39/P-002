import { describe, expect, it } from "vitest";

import { MockProjectRepository } from "@/repositories/mock/MockProjectRepository";

describe("MockProjectRepository", () => {
  it("returns isolated project data", async () => {
    const repository = new MockProjectRepository();
    const first = await repository.list();
    first[0].name = "changed locally";

    const second = await repository.list();
    expect(second[0].name).not.toBe("changed locally");
  });

  it("creates a visual project in analysis-pending state", async () => {
    const repository = new MockProjectRepository();
    const project = await repository.create({
      name: "sample",
      description: "Uploaded in a repository test",
      branch: "main",
      file: new File(["PK mock"], "sample.zip", { type: "application/zip" }),
    });

    expect(project.status).toBe("analyzing");
    expect((await repository.list())[0].name).toBe("sample");
  });
});
