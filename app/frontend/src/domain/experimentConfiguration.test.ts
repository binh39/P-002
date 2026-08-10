import { describe, expect, it } from "vitest";

import {
  defaultDatasetPercentages,
  selectCandidateFunctions,
  splitFunctions,
  type ExperimentFunction,
} from "@/domain/experimentConfiguration";

const functions: ExperimentFunction[] = Array.from({ length: 10 }, (_, index) => ({
  id: `fn-${index}`,
  key: `project:fn-${index}`,
  project: "project",
  projectName: "Project",
  file: "module.py",
  className: "",
  name: `function_${index}`,
  lines: `${index + 1}-${index + 2}`,
  loc: index + 2,
  statements: index + 1,
  branches: index,
  status: "Valid",
}));

describe("experiment dataset configuration", () => {
  it("defaults to a 20/40/40 train, validation, and test split", () => {
    expect(defaultDatasetPercentages).toEqual({ train: 20, validation: 40, test: 40 });
  });

  it("ranks the candidate pool before shuffling it", () => {
    const selected = selectCandidateFunctions(functions, "most_branches", 4, 42);
    expect(new Set(selected.map((item) => item.id))).toEqual(
      new Set(["fn-6", "fn-7", "fn-8", "fn-9"]),
    );
  });

  it("creates deterministic, disjoint percentage splits", () => {
    const first = splitFunctions(functions, { train: 50, validation: 30, test: 20 }, 7);
    const second = splitFunctions(functions, { train: 50, validation: 30, test: 20 }, 7);
    expect(first).toEqual(second);
    expect(first.train).toHaveLength(5);
    expect(first.validation).toHaveLength(3);
    expect(first.test).toHaveLength(2);
    expect(
      new Set(
        Object.values(first)
          .flat()
          .map((item) => item.key),
      ),
    ).toHaveLength(10);
  });
});
