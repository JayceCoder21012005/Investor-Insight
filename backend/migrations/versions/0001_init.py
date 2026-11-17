"""init: profiles, trades, reports

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

JSONType = sa.JSON().with_variant(JSONB(), "postgresql")
BigIntPk = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "profiles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("answers", JSONType, nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("tier", sa.String(), nullable=False),
        sa.Column("level", sa.String(), nullable=False),
        sa.Column("persona_id", sa.String(), nullable=True),
        sa.CheckConstraint("tier IN ('conservative','balanced','growth')", name="ck_profiles_tier"),
        sa.CheckConstraint("level IN ('beginner','intermediate','experienced')", name="ck_profiles_level"),
    )
    op.create_table(
        "trades",
        sa.Column("id", BigIntPk, primary_key=True, autoincrement=True),
        sa.Column("profile_id", sa.Uuid(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("row_no", sa.Integer(), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("side", sa.String(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price", sa.BigInteger(), nullable=False),
        sa.Column("fee", sa.BigInteger(), nullable=False),
        sa.Column("tax", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("side IN ('BUY','SELL')", name="ck_trades_side"),
        sa.CheckConstraint("quantity > 0", name="ck_trades_quantity"),
        sa.CheckConstraint("price > 0", name="ck_trades_price"),
        sa.CheckConstraint("fee >= 0", name="ck_trades_fee"),
        sa.CheckConstraint("tax >= 0", name="ck_trades_tax"),
    )
    op.create_index("ix_trades_profile_date", "trades", ["profile_id", "trade_date"])
    op.create_table(
        "reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("profile_id", sa.Uuid(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_hash", sa.String(), nullable=False),
        sa.Column("formula_version", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("violations", JSONType, nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("metrics", JSONType, nullable=False),
        sa.Column("content", JSONType, nullable=False),
    )
    op.create_index("ix_reports_profile_created", "reports", ["profile_id", sa.text("created_at DESC")])


def downgrade() -> None:
    op.drop_index("ix_reports_profile_created", table_name="reports")
    op.drop_table("reports")
    op.drop_index("ix_trades_profile_date", table_name="trades")
    op.drop_table("trades")
    op.drop_table("profiles")
