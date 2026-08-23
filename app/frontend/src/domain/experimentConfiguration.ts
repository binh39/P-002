import type { ProjectFunction } from "@/domain/projects";

export type SamplingMethod = "random" | "most_branches" | "most_statements" | "manual";
export type DatasetSplit = "train" | "validation" | "test";

export interface ExperimentFunction extends ProjectFunction {
  key: string;
  projectName: string;
}

export interface DatasetPercentages {
  train: number;
  validation: number;
  test: number;
}

export interface CloudExperimentSettings {
  coverupModel: string;
  optimizeModel: string;
  maxAttempts: number;
  repeatTests: number;
  maxConcurrency: number;
  rateLimit: number | null;
  pytestArgs: string;
  budgetMode: "light" | "medium" | "heavy" | "custom";
  maxMetricCalls: number;
  evaluationReplicates: number;
  reflectionTemperature: number;
}

export const defaultDatasetPercentages: DatasetPercentages = {
  train: 20,
  validation: 40,
  test: 40,
};

export const defaultCloudSettings: CloudExperimentSettings = {
  coverupModel: "vertex_ai/gemini-3.5-flash-lite",
  optimizeModel: "vertex_ai/gemini-3.6-flash",
  maxAttempts: 4,
  repeatTests: 5,
  maxConcurrency: 10,
  rateLimit: null,
  pytestArgs: "",
  budgetMode: "custom",
  maxMetricCalls: 30,
  evaluationReplicates: 1,
  reflectionTemperature: 0.7,
};

function hashSeed(value: string) {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function seededRandom(seed: number) {
  let value = seed >>> 0;
  return () => {
    value += 0x6d2b79f5;
    let result = value;
    result = Math.imul(result ^ (result >>> 15), result | 1);
    result ^= result + Math.imul(result ^ (result >>> 7), result | 61);
    return ((result ^ (result >>> 14)) >>> 0) / 4294967296;
  };
}

export function deterministicShuffle<T>(items: T[], seed: number): T[] {
  const shuffled = [...items];
  const random = seededRandom(seed);
  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(random() * (index + 1));
    [shuffled[index], shuffled[swapIndex]] = [shuffled[swapIndex], shuffled[index]];
  }
  return shuffled;
}

export function selectCandidateFunctions(
  functions: ExperimentFunction[],
  method: Exclude<SamplingMethod, "manual">,
  limit: number | null,
  seed: number,
) {
  const valid = functions.filter((item) => item.status === "Valid");
  const stable = [...valid].sort((left, right) => left.key.localeCompare(right.key));
  const selectedCount = limit ?? stable.length;
  if (method === "random") return deterministicShuffle(stable, seed).slice(0, selectedCount);

  const ranked = stable.sort((left, right) => {
    if (method === "most_branches") {
      return (
        right.branches - left.branches ||
        right.statements - left.statements ||
        right.loc - left.loc ||
        left.key.localeCompare(right.key)
      );
    }
    return (
      right.statements - left.statements ||
      right.branches - left.branches ||
      right.loc - left.loc ||
      left.key.localeCompare(right.key)
    );
  });

  // Ranking chooses the candidate pool. Only then is it shuffled for unbiased splitting.
  return deterministicShuffle(ranked.slice(0, selectedCount), seed);
}

function allocateCounts(total: number, percentages: DatasetPercentages) {
  const names: DatasetSplit[] = ["train", "validation", "test"];
  const exact = names.map((name) => ({ name, value: (total * percentages[name]) / 100 }));
  const counts = Object.fromEntries(
    exact.map(({ name, value }) => [name, Math.floor(value)]),
  ) as Record<DatasetSplit, number>;
  let remaining = total - names.reduce((sum, name) => sum + counts[name], 0);
  exact
    .sort(
      (left, right) =>
        (right.value % 1) - (left.value % 1) ||
        names.indexOf(left.name) - names.indexOf(right.name),
    )
    .forEach(({ name }) => {
      if (remaining > 0) {
        counts[name] += 1;
        remaining -= 1;
      }
    });
  if (total >= names.filter((name) => percentages[name] > 0).length) {
    names.forEach((name) => {
      if (percentages[name] === 0 || counts[name] > 0) return;
      const donor = [...names]
        .filter((candidate) => counts[candidate] > 1)
        .sort((left, right) => counts[right] - counts[left])[0];
      if (donor) {
        counts[donor] -= 1;
        counts[name] += 1;
      }
    });
  }
  return counts;
}

export function splitFunctions(
  functions: ExperimentFunction[],
  percentages: DatasetPercentages,
  seed: number,
) {
  const shuffled = deterministicShuffle(functions, hashSeed(`${seed}:dataset`));
  const counts = allocateCounts(shuffled.length, percentages);
  const trainEnd = counts.train;
  const validationEnd = trainEnd + counts.validation;
  return {
    train: shuffled.slice(0, trainEnd),
    validation: shuffled.slice(trainEnd, validationEnd),
    test: shuffled.slice(validationEnd),
  } satisfies Record<DatasetSplit, ExperimentFunction[]>;
}

export function percentagesAreValid(percentages: DatasetPercentages) {
  return (
    Object.values(percentages).every(
      (value) => Number.isInteger(value) && value >= 0 && value <= 100,
    ) &&
    percentages.train + percentages.validation + percentages.test === 100 &&
    percentages.test > 0
  );
}
