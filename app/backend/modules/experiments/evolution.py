"""Parse the human-readable GEPA Cloud Run log into UI-safe evolution events."""

from __future__ import annotations

import ast
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime

from .schemas import EvolutionIteration, EvolutionMetricPoint, EvolutionResponse

_ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_ITERATION = re.compile(r"Iteration\s+(\d+):\s*(.*)", re.DOTALL)
_BASELINE = re.compile(r"Base program full valset score:\s*([-+\d.eE]+)")
_SELECTED = re.compile(r"Selected program\s+(\d+)\s+score:\s*([-+\d.eE]+)")
_PROPOSAL = re.compile(r"Proposed new text for\s+([^:]+):\s*(.*)", re.DOTALL)
_SUBSAMPLE_REJECTED = re.compile(
    r"New subsample score\s+([-+\d.eE]+)\s+is not better than old score\s+([-+\d.eE]+)"
)
_SUBSAMPLE_ACCEPTED = re.compile(
    r"New subsample score\s+([-+\d.eE]+)\s+is better than old score\s+([-+\d.eE]+)"
)
_MERGE_REJECTED = re.compile(
    r"New program subsample score\s+([-+\d.eE]+)\s+is worse than both parents\s+(.+?),\s*skipping merge"
)
_MERGE_PAIR = re.compile(r"(?:Skipping merge of|Merge of)\s+(\d+)\s+and\s+(\d+)")
_OBJECTIVES = re.compile(r"Objective pareto front scores:\s*(\{.*\})")
_PARETO_SCORE = re.compile(r"Valset pareto front aggregate score:\s*([-+\d.eE]+)")


@dataclass(frozen=True)
class CloudLogLine:
    timestamp: datetime | None
    text: str


@dataclass
class _IterationState:
    iteration: int
    strategy: str = "pending"
    parent_program: str | None = None
    parent_validation_score: float | None = None
    component: str | None = None
    proposed_prompt_parts: list[str] = field(default_factory=list)
    parent_minibatch_sum: float | None = None
    candidate_minibatch_sum: float | None = None
    decision: str = "Pending"
    full_validation: bool = False
    best_statement: float | None = None
    best_branch: float | None = None
    best_score: float | None = None
    pareto_changed: bool = False


def _number(value: str) -> float | None:
    try:
        return float(value.rstrip(".,;"))
    except (TypeError, ValueError):
        return None


def _literal_mapping(value: str) -> dict:
    try:
        parsed = ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _clean_lines(entries: Iterable[CloudLogLine]) -> list[str]:
    ordered = sorted(
        entries,
        key=lambda item: item.timestamp.timestamp() if item.timestamp is not None else float("-inf"),
    )
    lines: list[str] = []
    for entry in ordered:
        text = _ANSI.sub("", str(entry.text)).replace("\r", "\n")
        lines.extend(text.splitlines())
    return lines


def parse_evolution_log(entries: Iterable[CloudLogLine]) -> EvolutionResponse:
    """Build a best-effort evolution timeline from GEPA's stable display log."""
    states: dict[int, _IterationState] = {}
    proposal_iteration: int | None = None

    def state(index: int) -> _IterationState:
        return states.setdefault(index, _IterationState(iteration=index))

    for raw_line in _clean_lines(entries):
        line = raw_line.strip()
        match = _ITERATION.search(line)
        if match:
            index = int(match.group(1))
            body = match.group(2).strip()
            current = state(index)
            proposal_iteration = None

            if baseline := _BASELINE.search(body):
                current.strategy = "baseline"
                current.parent_program = "Program 0"
                current.parent_validation_score = _number(baseline.group(1))
                current.best_score = current.parent_validation_score
                current.decision = "Baseline evaluated"
                current.full_validation = True
                current.pareto_changed = True
                continue
            if selected := _SELECTED.search(body):
                current.strategy = "reflective mutation"
                current.parent_program = f"Program {selected.group(1)}"
                current.parent_validation_score = _number(selected.group(2))
                continue
            if proposal := _PROPOSAL.search(body):
                current.strategy = "reflective mutation"
                current.component = proposal.group(1).strip()
                first_line = proposal.group(2).rstrip()
                if first_line:
                    current.proposed_prompt_parts.append(first_line)
                proposal_iteration = index
                continue
            if rejected := _SUBSAMPLE_REJECTED.search(body):
                current.candidate_minibatch_sum = _number(rejected.group(1))
                current.parent_minibatch_sum = _number(rejected.group(2))
                current.decision = "Rejected"
                continue
            if accepted := _SUBSAMPLE_ACCEPTED.search(body):
                current.candidate_minibatch_sum = _number(accepted.group(1))
                current.parent_minibatch_sum = _number(accepted.group(2))
                current.decision = "Accepted"
                current.full_validation = True
                continue
            if merge_rejected := _MERGE_REJECTED.search(body):
                current.strategy = "merge"
                current.candidate_minibatch_sum = _number(merge_rejected.group(1))
                parents = _literal_mapping(merge_rejected.group(2))
                numeric_parents = {
                    str(key): _number(str(value)) for key, value in parents.items()
                }
                numeric_parents = {key: value for key, value in numeric_parents.items() if value is not None}
                if numeric_parents:
                    current.parent_program = " + ".join(f"Program {key}" for key in numeric_parents)
                    current.parent_minibatch_sum = max(numeric_parents.values())
                current.decision = "Rejected"
                continue
            if "No merge candidates" in body:
                current.strategy = "reflective mutation"
                continue
            if pair := _MERGE_PAIR.search(body):
                current.strategy = "merge"
                current.parent_program = f"Program {pair.group(1)} + Program {pair.group(2)}"
                if "Skipping merge" in body:
                    current.decision = "Rejected"
                continue
            if objectives := _OBJECTIVES.search(body):
                values = _literal_mapping(objectives.group(1))
                current.best_statement = _number(str(values.get("statement")))
                current.best_branch = _number(str(values.get("branch")))
                current.pareto_changed = True
                continue
            if aggregate := _PARETO_SCORE.search(body):
                current.best_score = _number(aggregate.group(1))
                current.pareto_changed = True
                if current.decision == "Pending":
                    current.decision = "Accepted"
                    current.full_validation = True
                continue
            continue

        if proposal_iteration is not None:
            # tqdm/status lines delimit a multiline proposal but are not prompt text.
            if line.startswith("GEPA Optimization:") or line.startswith("Saved optimized program"):
                proposal_iteration = None
            else:
                states[proposal_iteration].proposed_prompt_parts.append(raw_line.rstrip())

    if not states:
        return EvolutionResponse(
            available=False,
            source="cloud_run_stdout",
            message="Cloud Run has not published GEPA iteration logs yet.",
        )

    last_statement: float | None = None
    last_branch: float | None = None
    last_score: float | None = None
    iterations: list[EvolutionIteration] = []
    metrics: list[EvolutionMetricPoint] = []
    for index in sorted(states):
        current = states[index]
        changed = current.pareto_changed
        if current.best_statement is not None:
            last_statement = current.best_statement
        if current.best_branch is not None:
            last_branch = current.best_branch
        if current.best_score is not None:
            last_score = current.best_score
        current.best_statement = last_statement
        current.best_branch = last_branch
        current.best_score = last_score
        prompt = "\n".join(current.proposed_prompt_parts).strip() or None
        iterations.append(
            EvolutionIteration(
                iteration=index,
                strategy=current.strategy,
                parent_program=current.parent_program,
                parent_validation_score=current.parent_validation_score,
                component=current.component,
                proposed_prompt=prompt,
                parent_minibatch_sum=current.parent_minibatch_sum,
                candidate_minibatch_sum=current.candidate_minibatch_sum,
                decision=current.decision,
                full_validation=current.full_validation,
                best_statement=current.best_statement,
                best_branch=current.best_branch,
                best_score=current.best_score,
                pareto_changed=changed,
            )
        )
        metrics.append(
            EvolutionMetricPoint(
                iteration=index,
                statement=current.best_statement,
                branch=current.best_branch,
                score=current.best_score,
            )
        )

    return EvolutionResponse(
        available=True,
        source="cloud_run_stdout",
        message="Parsed from Cloud Run stdout; target-level details are not available.",
        iterations=iterations,
        metrics=metrics,
    )
