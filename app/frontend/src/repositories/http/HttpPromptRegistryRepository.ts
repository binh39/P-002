import { apiRequest } from "@/api/client";
import type {
  ExperimentStatus,
  PromptBundle,
  PromptCoverageMetrics,
  PromptRegistryEntry,
  PromptRegistryList,
  PromptSnapshot,
} from "@/domain/experiments";
import type { PromptRegistryRepository } from "@/repositories/contracts/PromptRegistryRepository";

interface ApiCoverageMetrics {
  score: number | null;
  statement_coverage: number | null;
  branch_coverage: number | null;
  pass_rate: number | null;
}

interface ApiPromptSnapshot {
  id: string;
  experiment_id: string;
  role: PromptSnapshot["role"];
  origin: PromptSnapshot["origin"];
  prompt_digest: string;
  prompt: PromptBundle;
  source_snapshot_digest: string;
  dataset_digest: string;
  split_seed: number;
  runner_protocol_version: number;
  coverup_model: string;
  optimize_model: string;
  metrics: ApiCoverageMetrics;
  estimated_cost_usd: number | null;
  created_at: string;
}

interface ApiPromptRegistryEntry {
  experiment_id: string;
  experiment_name: string;
  project_ids: string[];
  project_names: string[];
  status: ExperimentStatus;
  baseline: ApiPromptSnapshot;
  optimized: ApiPromptSnapshot | null;
  baseline_metrics: ApiCoverageMetrics;
  optimized_metrics: ApiCoverageMetrics;
  absolute_gain: number | null;
  created_at: string;
  updated_at: string;
}

interface ApiPromptRegistryList {
  items: ApiPromptRegistryEntry[];
  total: number;
  offset: number;
  limit: number;
}

function mapCoverageMetrics(metrics: ApiCoverageMetrics): PromptCoverageMetrics {
  return {
    score: metrics.score,
    statementCoverage: metrics.statement_coverage,
    branchCoverage: metrics.branch_coverage,
    passRate: metrics.pass_rate,
  };
}

function mapSnapshot(snapshot: ApiPromptSnapshot): PromptSnapshot {
  return {
    id: snapshot.id,
    experimentId: snapshot.experiment_id,
    role: snapshot.role,
    origin: snapshot.origin,
    promptDigest: snapshot.prompt_digest,
    prompt: snapshot.prompt,
    sourceSnapshotDigest: snapshot.source_snapshot_digest,
    datasetDigest: snapshot.dataset_digest,
    splitSeed: snapshot.split_seed,
    runnerProtocolVersion: snapshot.runner_protocol_version,
    coverupModel: snapshot.coverup_model,
    optimizeModel: snapshot.optimize_model,
    metrics: mapCoverageMetrics(snapshot.metrics),
    estimatedCostUsd: snapshot.estimated_cost_usd,
    createdAt: snapshot.created_at,
  };
}

function mapEntry(entry: ApiPromptRegistryEntry): PromptRegistryEntry {
  return {
    experimentId: entry.experiment_id,
    experimentName: entry.experiment_name,
    projectIds: entry.project_ids,
    projectNames: entry.project_names,
    status: entry.status,
    baseline: mapSnapshot(entry.baseline),
    optimized: entry.optimized ? mapSnapshot(entry.optimized) : null,
    baselineMetrics: mapCoverageMetrics(entry.baseline_metrics),
    optimizedMetrics: mapCoverageMetrics(entry.optimized_metrics),
    absoluteGain: entry.absolute_gain,
    createdAt: entry.created_at,
    updatedAt: entry.updated_at,
  };
}

export class HttpPromptRegistryRepository implements PromptRegistryRepository {
  async list(signal?: AbortSignal): Promise<PromptRegistryList> {
    const response = await apiRequest<ApiPromptRegistryList>("/prompt-registry?limit=50", {
      signal,
    });
    return { ...response, items: response.items.map(mapEntry) };
  }

  async get(experimentId: string, signal?: AbortSignal): Promise<PromptRegistryEntry> {
    return mapEntry(
      await apiRequest<ApiPromptRegistryEntry>(`/prompt-registry/${experimentId}`, { signal }),
    );
  }
}
