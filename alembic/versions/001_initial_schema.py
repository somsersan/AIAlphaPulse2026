"""Initial schema — assets, ohlcv_data, scoring_results (PRODUCT_SPEC §4.3).

Revision ID: 001
Revises:
Create Date: 2026-02-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── assets ────────────────────────────────────────────────────────────────
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column(
            "asset_type",
            sa.String(length=20),
            nullable=True,
        ),
        sa.Column("exchange", sa.String(length=50), nullable=True),
        sa.Column("sector", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "asset_type IN ('stock', 'crypto')", name="ck_assets_type"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker"),
    )

    # ── ohlcv_data ────────────────────────────────────────────────────────────
    op.create_table(
        "ohlcv_data",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("open", sa.DECIMAL(precision=20, scale=8), nullable=True),
        sa.Column("high", sa.DECIMAL(precision=20, scale=8), nullable=True),
        sa.Column("low", sa.DECIMAL(precision=20, scale=8), nullable=True),
        sa.Column("close", sa.DECIMAL(precision=20, scale=8), nullable=True),
        sa.Column("volume", sa.DECIMAL(precision=30, scale=8), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "timestamp", name="uq_ohlcv_asset_time"),
    )
    op.create_index("idx_ohlcv_asset_time", "ohlcv_data", ["asset_id", "timestamp"])

    # ── scoring_results ───────────────────────────────────────────────────────
    op.create_table(
        "scoring_results",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column(
            "timestamp",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # 7 factor scores
        sa.Column("trend_score", sa.DECIMAL(precision=6, scale=2), nullable=True),
        sa.Column("volatility_score", sa.DECIMAL(precision=6, scale=2), nullable=True),
        sa.Column("sentiment_score", sa.DECIMAL(precision=6, scale=2), nullable=True),
        sa.Column("fundamental_score", sa.DECIMAL(precision=6, scale=2), nullable=True),
        sa.Column(
            "relative_strength_score", sa.DECIMAL(precision=6, scale=2), nullable=True
        ),
        sa.Column(
            "insider_funds_score", sa.DECIMAL(precision=6, scale=2), nullable=True
        ),
        sa.Column("macro_score", sa.DECIMAL(precision=6, scale=2), nullable=True),
        # Composite score & signal
        sa.Column("ai_score", sa.DECIMAL(precision=6, scale=2), nullable=False),
        sa.Column("signal", sa.String(length=20), nullable=True),
        sa.Column("explanation", sa.TEXT(), nullable=True),
        # Metadata
        sa.Column("data_freshness_seconds", sa.Integer(), nullable=True),
        sa.Column("model_version", sa.String(length=10), nullable=True),
        sa.CheckConstraint(
            "signal IN ('STRONG BUY', 'BUY', 'NEUTRAL', 'SELL', 'STRONG SELL')",
            name="ck_scoring_signal",
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "timestamp", name="uq_scores_asset_time"),
    )
    op.create_index(
        "idx_scores_asset", "scoring_results", ["asset_id", "timestamp"]
    )
    op.create_index("idx_scores_value", "scoring_results", ["ai_score"])


def downgrade() -> None:
    op.drop_index("idx_scores_value", table_name="scoring_results")
    op.drop_index("idx_scores_asset", table_name="scoring_results")
    op.drop_table("scoring_results")

    op.drop_index("idx_ohlcv_asset_time", table_name="ohlcv_data")
    op.drop_table("ohlcv_data")

    op.drop_table("assets")
