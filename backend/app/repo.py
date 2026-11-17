"""Persistence helpers: the only place that turns API/core models into rows and back."""
from __future__ import annotations

import hashlib
import uuid
from collections.abc import Sequence

from sqlalchemy import delete
from sqlmodel import Session, col, select

from app.models import Profile, Report, Trade
from app.schemas import PricedTrade


def create_profile(session: Session, answers: list[int], score: int, tier: str, level: str,
                   persona_id: str | None = None) -> Profile:
    profile = Profile(answers=answers, score=score, tier=tier, level=level, persona_id=persona_id)
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


def get_profile(session: Session, profile_id: uuid.UUID) -> Profile | None:
    return session.get(Profile, profile_id)


def _side(t) -> str:
    return t.side.value if hasattr(t.side, "value") else t.side


def replace_trades(session: Session, profile_id: uuid.UUID, trades: Sequence[PricedTrade]) -> None:
    """Delete the profile's trades and insert the new ones in ONE transaction."""
    try:
        session.exec(delete(Trade).where(col(Trade.profile_id) == profile_id))
        session.add_all([
            Trade(profile_id=profile_id, row_no=t.row_no, trade_date=t.trade_date, symbol=t.symbol,
                  side=_side(t), quantity=t.quantity, price=t.price, fee=t.fee, tax=t.tax)
            for t in trades
        ])
        session.commit()
    except Exception:
        session.rollback()
        raise


def list_trades(session: Session, profile_id: uuid.UUID) -> list[Trade]:
    stmt = (select(Trade).where(Trade.profile_id == profile_id)
            .order_by(col(Trade.trade_date), col(Trade.row_no)))
    return list(session.exec(stmt))


def data_hash(trades: Sequence[PricedTrade], formula_version: str) -> str:
    """sha256 over the sorted trades CSV plus the formula version (order-insensitive)."""
    lines = sorted(
        f"{t.trade_date},{t.symbol},{_side(t)},{t.quantity},{t.price},{t.fee},{t.tax}" for t in trades
    )
    return hashlib.sha256(("\n".join(lines) + "|" + formula_version).encode()).hexdigest()


def save_report(session: Session, profile_id: uuid.UUID, *, data_hash: str, formula_version: str,
                model: str, attempts: int, passed: bool, violations: list, latency_ms: int,
                metrics: dict, content: dict) -> Report:
    report = Report(profile_id=profile_id, data_hash=data_hash, formula_version=formula_version,
                    model=model, attempts=attempts, passed=passed, violations=violations,
                    latency_ms=latency_ms, metrics=metrics, content=content)
    session.add(report)
    session.commit()
    session.refresh(report)
    return report


def find_report_by_hash(session: Session, profile_id: uuid.UUID, hash_: str) -> Report | None:
    stmt = (select(Report).where(Report.profile_id == profile_id, Report.data_hash == hash_)
            .order_by(col(Report.created_at).desc()))
    return session.exec(stmt).first()


def latest_report(session: Session, profile_id: uuid.UUID) -> Report | None:
    stmt = select(Report).where(Report.profile_id == profile_id).order_by(col(Report.created_at).desc())
    return session.exec(stmt).first()
