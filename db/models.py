from __future__ import annotations

import datetime
import enum
import uuid

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


def new_id() -> str:
    return str(uuid.uuid4())


class PromptStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    OPTIMIZED = "OPTIMIZED"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    baseline_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    module_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    dataset_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_root: Mapped[str] = mapped_column(String(1000), nullable=False)
    budget_limit: Mapped[float] = mapped_column(Float, default=5.0)
    status: Mapped[PromptStatus] = mapped_column(
        Enum(PromptStatus),
        default=PromptStatus.DRAFT,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC),
    )
    candidates: Mapped[list[Candidate]] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
    )


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    experiment_id: Mapped[str] = mapped_column(
        ForeignKey("experiments.id"),
        index=True,
    )
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("candidates.id"),
        nullable=True,
    )
    generation: Mapped[int] = mapped_column(Integer, default=0)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    fitness_score: Mapped[float] = mapped_column(Float, default=0.0)
    pass_rate: Mapped[float] = mapped_column(Float, default=0.0)
    statement_coverage: Mapped[float] = mapped_column(Float, default=0.0)
    branch_coverage: Mapped[float] = mapped_column(Float, default=0.0)
    mutation_score: Mapped[float] = mapped_column(Float, default=0.0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[PromptStatus] = mapped_column(
        Enum(PromptStatus),
        default=PromptStatus.OPTIMIZED,
    )
    experiment: Mapped[Experiment] = relationship(back_populates="candidates")
    approvals: Mapped[list[Approval]] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
    )


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidates.id"),
        index=True,
    )
    reviewer_id: Mapped[str] = mapped_column(String(200), nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC),
    )
    candidate: Mapped[Candidate] = relationship(back_populates="approvals")
