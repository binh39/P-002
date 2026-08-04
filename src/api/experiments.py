from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from analytics.pareto import compute_pareto_frontier
from db import crud
from db.base import get_session
from db.models import Candidate, PromptStatus
from db.schemas import (
    ApprovalOut,
    CandidateOut,
    ExperimentCreate,
    ExperimentOut,
    ReviewRequest,
)
from src.services.experiments import execute_experiment

router = APIRouter(prefix="/experiments", tags=["experiments"])
review_router = APIRouter(prefix="/candidates", tags=["review"])


def _experiment_or_404(session: Session, experiment_id: str):
    experiment = crud.get_experiment(session, experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment


def _candidate_or_404(session: Session, candidate_id: str) -> Candidate:
    candidate = session.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


@router.post("", response_model=ExperimentOut, status_code=status.HTTP_201_CREATED)
def create_experiment_endpoint(
    payload: ExperimentCreate,
    session: Session = Depends(get_session),
):
    return crud.create_experiment(session, payload)


@router.get("", response_model=list[ExperimentOut])
def list_experiments_endpoint(session: Session = Depends(get_session)):
    return crud.list_experiments(session)


@router.get("/{experiment_id}", response_model=ExperimentOut)
def get_experiment_endpoint(
    experiment_id: str,
    session: Session = Depends(get_session),
):
    return _experiment_or_404(session, experiment_id)


@router.post("/{experiment_id}/run", status_code=status.HTTP_202_ACCEPTED)
def run_experiment_endpoint(
    experiment_id: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    experiment = _experiment_or_404(session, experiment_id)
    if experiment.status not in {PromptStatus.DRAFT, PromptStatus.FAILED}:
        raise HTTPException(status_code=409, detail="Experiment has already been run")
    background_tasks.add_task(execute_experiment, experiment.id)
    return {"status": "running", "experiment_id": experiment.id}


@router.get("/{experiment_id}/candidates", response_model=list[CandidateOut])
def list_candidates_endpoint(
    experiment_id: str,
    session: Session = Depends(get_session),
):
    _experiment_or_404(session, experiment_id)
    return crud.list_candidates(session, experiment_id)


@router.get("/{experiment_id}/pareto", response_model=list[CandidateOut])
def pareto_endpoint(
    experiment_id: str,
    session: Session = Depends(get_session),
):
    rows = list_candidates_endpoint(experiment_id, session)
    candidates = [CandidateOut.model_validate(row).model_dump() for row in rows]
    frontier = compute_pareto_frontier(
        candidates,
        maximize=["fitness_score"],
        minimize=["latency_seconds"],
    )
    return [CandidateOut.model_validate(candidate) for candidate in frontier]


def _review(
    candidate_id: str,
    payload: ReviewRequest,
    decision: str,
    session: Session,
):
    candidate = _candidate_or_404(session, candidate_id)
    if candidate.status in {PromptStatus.APPROVED, PromptStatus.REJECTED}:
        raise HTTPException(status_code=409, detail="Candidate has already been reviewed")
    return crud.review_candidate(
        session,
        candidate,
        reviewer_id=payload.reviewer_id,
        decision=decision,
        comment=payload.comment,
    )


@review_router.post("/{candidate_id}/approve", response_model=ApprovalOut)
def approve_candidate_endpoint(
    candidate_id: str,
    payload: ReviewRequest,
    session: Session = Depends(get_session),
):
    return _review(candidate_id, payload, "approved", session)


@review_router.post("/{candidate_id}/reject", response_model=ApprovalOut)
def reject_candidate_endpoint(
    candidate_id: str,
    payload: ReviewRequest,
    session: Session = Depends(get_session),
):
    return _review(candidate_id, payload, "rejected", session)
