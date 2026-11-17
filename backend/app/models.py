"""SQLModel tables. Separate from API models (app/schemas.py); convert explicitly."""
import threading
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    desc,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

JSONType = JSON().with_variant(JSONB(), "postgresql")
BigIntPk = BigInteger().with_variant(Integer(), "sqlite")  # SQLite only autoincrements INTEGER keys


_last_ts = datetime.min.replace(tzinfo=UTC)
_ts_lock = threading.Lock()


def utcnow() -> datetime:
    """Strictly increasing in this process: coarse OS clocks must not tie "latest report" ordering."""
    global _last_ts
    with _ts_lock:
        now = datetime.now(UTC)
        if now <= _last_ts:
            now = _last_ts + timedelta(microseconds=1)
        _last_ts = now
        return now


class Profile(SQLModel, table=True):
    __tablename__ = "profiles"
    __table_args__ = (
        CheckConstraint("tier IN ('conservative','balanced','growth')", name="ck_profiles_tier"),
        CheckConstraint("level IN ('beginner','intermediate','experienced')", name="ck_profiles_level"),
    )
    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=Column(Uuid, primary_key=True))
    created_at: datetime = Field(default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))
    answers: list = Field(sa_column=Column(JSONType, nullable=False))
    score: int = Field(sa_column=Column(Integer, nullable=False))
    tier: str = Field(sa_column=Column(String, nullable=False))
    level: str = Field(sa_column=Column(String, nullable=False))
    persona_id: str | None = Field(default=None, sa_column=Column(String, nullable=True))


class Trade(SQLModel, table=True):
    __tablename__ = "trades"
    __table_args__ = (
        CheckConstraint("side IN ('BUY','SELL')", name="ck_trades_side"),
        CheckConstraint("quantity > 0", name="ck_trades_quantity"),
        CheckConstraint("price > 0", name="ck_trades_price"),
        CheckConstraint("fee >= 0", name="ck_trades_fee"),
        CheckConstraint("tax >= 0", name="ck_trades_tax"),
        Index("ix_trades_profile_date", "profile_id", "trade_date"),
    )
    id: int | None = Field(default=None, sa_column=Column(BigIntPk, primary_key=True, autoincrement=True))
    profile_id: uuid.UUID = Field(
        sa_column=Column(Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False))
    row_no: int = Field(sa_column=Column(Integer, nullable=False))
    trade_date: date = Field(sa_column=Column(Date, nullable=False))
    symbol: str = Field(sa_column=Column(String, nullable=False))
    side: str = Field(sa_column=Column(String, nullable=False))
    quantity: int = Field(sa_column=Column(Integer, nullable=False))
    price: int = Field(sa_column=Column(BigInteger, nullable=False))
    fee: int = Field(sa_column=Column(BigInteger, nullable=False))
    tax: int = Field(sa_column=Column(BigInteger, nullable=False))


class Report(SQLModel, table=True):
    __tablename__ = "reports"
    __table_args__ = (Index("ix_reports_profile_created", "profile_id", desc("created_at")),)
    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=Column(Uuid, primary_key=True))
    profile_id: uuid.UUID = Field(
        sa_column=Column(Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False))
    created_at: datetime = Field(default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))
    data_hash: str = Field(sa_column=Column(String, nullable=False))
    formula_version: str = Field(sa_column=Column(String, nullable=False))
    model: str = Field(sa_column=Column(String, nullable=False))
    attempts: int = Field(sa_column=Column(Integer, nullable=False))
    passed: bool = Field(sa_column=Column(Boolean, nullable=False))
    violations: list = Field(sa_column=Column(JSONType, nullable=False))
    latency_ms: int = Field(sa_column=Column(Integer, nullable=False))
    metrics: dict = Field(sa_column=Column(JSONType, nullable=False))
    content: dict = Field(sa_column=Column(JSONType, nullable=False))
