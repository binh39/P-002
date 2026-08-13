import asyncio
from collections import defaultdict
from datetime import UTC, datetime

from backend.modules.experiments.repository import ExperimentRepository
from backend.modules.experiments.schemas import ExperimentStatus

from .schemas import (
    CoveragePoint,
    DashboardExperiment,
    DashboardKpi,
    DashboardResponse,
    QuickStat,
)

_RUNNING = {
    ExperimentStatus.BASELINE_RUNNING,
    ExperimentStatus.OPTIMIZING,
    ExperimentStatus.CANDIDATE_EVALUATING,
    ExperimentStatus.COMPARING,
}
_PENDING = {
    ExperimentStatus.DRAFT,
    ExperimentStatus.BASELINE_QUEUED,
    ExperimentStatus.OPTIMIZATION_QUEUED,
    ExperimentStatus.COMPARISON_QUEUED,
}
_FAILED = {
    ExperimentStatus.FAILED,
    ExperimentStatus.TIMED_OUT,
    ExperimentStatus.CANCELLED,
}


def _percent(value) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0
    if 0 <= number <= 1:
        number *= 100
    return round(max(0, min(number, 100)), 2)


def _status(value: ExperimentStatus) -> str:
    if value in _RUNNING:
        return "running"
    if value in _PENDING:
        return "pending"
    if value in _FAILED:
        return "failed"
    return "completed"


class DashboardService:
    def __init__(self, experiments: ExperimentRepository):
        self.experiments = experiments

    async def snapshot(self, owner_id: str) -> DashboardResponse:
        items = await self.experiments.list_for_owner(owner_id)
        runs = await asyncio.gather(
            *(
                self.experiments.get_optimization_run(item.optimization_run_id) if item.optimization_run_id else _none()
                for item in items
            )
        )
        pairs = list(zip(items, runs, strict=True))
        completed_metrics: list[tuple[datetime, float, float]] = []
        durations: list[float] = []
        gains: list[float] = []
        total_metric_calls = 0
        summaries: list[DashboardExperiment] = []

        for item, run in pairs:
            coverage = {}
            if run is not None:
                coverage = run.final_validation.get("optimized_aggregate_coverage") or {}
                total_metric_calls += run.metric_calls
                if run.started_at and run.finished_at:
                    durations.append(max(0, (run.finished_at - run.started_at).total_seconds()))
                gain = run.final_validation.get("absolute_gain")
                if gain is not None:
                    gains.append(float(gain))
            branch = _percent(coverage.get("branch_coverage"))
            statement = _percent(coverage.get("statement_coverage"))
            if run is not None and run.finished_at and (branch or statement):
                completed_metrics.append((run.finished_at, branch, statement))
            summaries.append(
                DashboardExperiment(
                    id=item.id[:8],
                    name=item.name,
                    model=item.settings.optimize_model.removeprefix("vertex_ai/"),
                    branch_coverage=branch,
                    statement_coverage=statement,
                    status=_status(item.status),
                    updated_at=item.updated_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC"),
                )
            )

        daily: dict[str, list[tuple[float, float]]] = defaultdict(list)
        for timestamp, branch, statement in completed_metrics:
            daily[timestamp.astimezone(UTC).date().isoformat()].append((branch, statement))
        coverage_points = [
            CoveragePoint(
                day=datetime.fromisoformat(day).strftime("%b %d"),
                branch=round(sum(value[0] for value in values) / len(values), 2),
                statement=round(sum(value[1] for value in values) / len(values), 2),
            )
            for day, values in sorted(daily.items())[-8:]
        ]
        latest_branch = completed_metrics[0][1] if completed_metrics else 0
        latest_statement = completed_metrics[0][2] if completed_metrics else 0
        running = sum(item.status in _RUNNING for item in items)
        queued = sum(item.status in _PENDING - {ExperimentStatus.DRAFT} for item in items)
        project_names = {snapshot.name for item in items for snapshot in item.project_snapshots if snapshot.name}
        project_name = (
            next(iter(project_names))
            if len(project_names) == 1
            else f"{len(project_names)} projects"
            if project_names
            else "Prompt research"
        )
        average_seconds = sum(durations) / len(durations) if durations else 0
        approved = sum(item.status == ExperimentStatus.APPROVED for item in items)
        models = {item.settings.coverup_model for item in items} | {item.settings.optimize_model for item in items}
        completed = sum(_status(item.status) == "completed" for item in items)

        return DashboardResponse(
            project_name=project_name,
            as_of=datetime.now(UTC).strftime("%B %d, %Y · %H:%M UTC"),
            coverage=coverage_points,
            kpis=[
                DashboardKpi(
                    label="Total Experiments",
                    value=str(len(items)),
                    delta="Owner-scoped records",
                    trend="neutral",
                    icon="experiments",
                ),
                DashboardKpi(
                    label="Running",
                    value=str(running),
                    delta=f"{queued} queued",
                    trend="neutral",
                    icon="running",
                ),
                DashboardKpi(
                    label="Branch Coverage",
                    value=f"{latest_branch:.1f}%",
                    delta="Latest completed run",
                    trend="neutral",
                    icon="branch",
                ),
                DashboardKpi(
                    label="Statement Coverage",
                    value=f"{latest_statement:.1f}%",
                    delta="Latest completed run",
                    trend="neutral",
                    icon="statement",
                ),
            ],
            quick_stats=[
                QuickStat(label="Avg. optimization time", value=_duration(average_seconds)),
                QuickStat(label="Metric calls", value=str(total_metric_calls)),
                QuickStat(label="Best coverage gain", value=f"{_percent(max(gains, default=0)):.1f}%"),
                QuickStat(label="Prompts approved", value=f"{approved} / {len(items)}"),
                QuickStat(label="Models in use", value=str(len(models))),
                QuickStat(label="Completed runs", value=str(completed)),
            ],
            experiments=summaries[:10],
        )


async def _none():
    return None


def _duration(seconds: float) -> str:
    if seconds <= 0:
        return "—"
    if seconds < 60:
        return f"{seconds:.0f} sec"
    return f"{seconds / 60:.1f} min"
