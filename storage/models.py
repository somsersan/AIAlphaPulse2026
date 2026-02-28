"""SQLAlchemy ORM models — mirrors PRODUCT_SPEC.md §4.3 schema."""
from sqlalchemy import (
    BigInteger, CheckConstraint, Column, ForeignKey, Index,
    Integer, String, DECIMAL, TIMESTAMP, TEXT, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class AssetDB(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), unique=True, nullable=False)
    name = Column(String(100))
    asset_type = Column(
        String(20),
        CheckConstraint("asset_type IN ('stock', 'crypto')", name="ck_assets_type"),
    )
    exchange = Column(String(50))
    sector = Column(String(50))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    ohlcv = relationship(
        "OHLCVDataDB", back_populates="asset", cascade="all, delete-orphan"
    )
    scores = relationship(
        "ScoringResultDB", back_populates="asset", cascade="all, delete-orphan"
    )


class OHLCVDataDB(Base):
    __tablename__ = "ohlcv_data"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    open = Column(DECIMAL(20, 8))
    high = Column(DECIMAL(20, 8))
    low = Column(DECIMAL(20, 8))
    close = Column(DECIMAL(20, 8))
    volume = Column(DECIMAL(30, 8))

    __table_args__ = (
        UniqueConstraint("asset_id", "timestamp", name="uq_ohlcv_asset_time"),
        Index("idx_ohlcv_asset_time", "asset_id", "timestamp"),
    )

    asset = relationship("AssetDB", back_populates="ohlcv")


class ScoringResultDB(Base):
    __tablename__ = "scoring_results"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    timestamp = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    # 7 factor scores
    trend_score = Column(DECIMAL(6, 2))
    volatility_score = Column(DECIMAL(6, 2))
    sentiment_score = Column(DECIMAL(6, 2))
    fundamental_score = Column(DECIMAL(6, 2))
    relative_strength_score = Column(DECIMAL(6, 2))
    insider_funds_score = Column(DECIMAL(6, 2))
    macro_score = Column(DECIMAL(6, 2))

    # Final composite score
    ai_score = Column(DECIMAL(6, 2), nullable=False)
    signal = Column(
        String(20),
        CheckConstraint(
            "signal IN ('STRONG BUY', 'BUY', 'NEUTRAL', 'SELL', 'STRONG SELL')",
            name="ck_scoring_signal",
        ),
    )
    explanation = Column(TEXT)

    # Metadata
    data_freshness_seconds = Column(Integer)
    model_version = Column(String(10))

    __table_args__ = (
        UniqueConstraint("asset_id", "timestamp", name="uq_scores_asset_time"),
        Index("idx_scores_asset", "asset_id", "timestamp"),
        Index("idx_scores_value", "ai_score"),
    )

    asset = relationship("AssetDB", back_populates="scores")
