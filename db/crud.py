from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Approval, Candidate, Experiment, PromptStatus
from .schemas import CandidateCreate, ExperimentCreate


def create_experiment(session: Session, payload: ExperimentCreate) -> Experiment:
    experiment = Experiment(**payload.model_dump())
    session.add(experiment)
    session.commit()
    session.refresh(experiment)
    return experiment


def get_experiment(session: Session, experiment_id: str) -> Experiment | None:
    return session.get(Experiment, experiment_id)


def list_experiments(session: Session) -> list[Experiment]:
    return list(session.scalars(select(Experiment).order_by(Experiment.created_at.desc())))


def set_experiment_status(
    session: Session,
    experiment: Experiment,
    status: PromptStatus,
    *,
    error_message: str | None = None,
) -> Experiment:
    experiment.status = status
    experiment.error_message = error_message
    session.commit()
    session.refresh(experiment)
    return experiment


def create_candidate(
    session: Session,
    experiment_id: str,
    payload: CandidateCreate,
) -> Candidate:
    candidate = Candidate(experiment_id=experiment_id, **payload.model_dump())
    session.add(candidate)
    session.commit()
    session.refresh(candidate)
    return candidate


def list_candidates(session: Session, experiment_id: str) -> list[Candidate]:
    statement = (
        select(Candidate)
        .where(Candidate.experiment_id == experiment_id)
        .order_by(Candidate.generation, Candidate.fitness_score.desc())
    )
    return list(session.scalars(statement))


def review_candidate(
    session: Session,
    candidate: Candidate,
    *,
    reviewer_id: str,
    decision: str,
    comment: str = "",
) -> Approval:
    if decision not in {"approved", "rejected"}:
        raise ValueError(f"Unsupported review decision: {decision}")
    status = (
        PromptStatus.APPROVED if decision == "approved" else PromptStatus.REJECTED
    )
    candidate.status = status
    candidate.experiment.status = status
    approval = Approval(
        candidate_id=candidate.id,
        reviewer_id=reviewer_id,
        decision=decision,
        comment=comment,
    )
    session.add(approval)
    session.commit()
    session.refresh(approval)
    return approval
