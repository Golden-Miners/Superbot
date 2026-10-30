"""M9.6 — News/sentiment only after core technical pipeline is reliable; permitted free sources.

Deterministic news/sentiment service:
- SentimentScore: normalized sentiment (-1 to 1) with source and timestamp
- NewsItem: a news article (headline, body, source, timestamp, symbol)
- NewsSource: enum of permitted free sources (RSS_FEED, FREE_NEWS_API)
- SentimentAnalyzer: keyword-based deterministic sentiment analysis
- SentimentResult: aggregated sentiment for a symbol over a window
- PipelineReliability: readiness flags for technical/risk/position pipeline
- SourceGate: blocks ingestion unless pipeline reliable
- Stdlib-only; no import-time network activity; free sources only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum


class NewsSource(str, Enum):
    """Permitted free news sources (no API key / no paid API)."""

    RSS_FEED = "rss_feed"
    FREE_NEWS_API = "free_news_api"


@dataclass(frozen=True)
class SentimentScore:
    """A normalized sentiment score for a single item."""

    score: Decimal  # -1 to 1
    source: NewsSource
    timestamp: datetime


@dataclass(frozen=True)
class NewsItem:
    """A single news article."""

    headline: str
    body: str
    source: NewsSource
    timestamp: datetime
    symbol: str


@dataclass(frozen=True)
class SentimentResult:
    """Aggregated sentiment for a symbol over a window."""

    symbol: str
    average_score: Decimal
    item_count: int
    latest_timestamp: datetime


@dataclass(frozen=True)
class PipelineReliability:
    """Readiness flags for the core technical pipeline."""

    technical_pipeline_reliable: bool
    risk_management_active: bool
    position_management_active: bool


@dataclass(frozen=True)
class SourceGate:
    """Gates news ingestion behind pipeline reliability."""

    reliability: PipelineReliability

    def allows_ingestion(self) -> bool:
        """Return True only when all pipeline flags are set."""
        return (
            self.reliability.technical_pipeline_reliable
            and self.reliability.risk_management_active
            and self.reliability.position_management_active
        )


class SentimentAnalyzer:
    """Deterministic keyword-based sentiment analyzer (no external model)."""

    POSITIVE_WORDS: frozenset[str] = frozenset(
        {
            "rally",
            "rallies",
            "rallied",
            "rise",
            "rises",
            "rose",
            "gain",
            "gains",
            "gained",
            "strong",
            "strongly",
            "bullish",
            "beat",
            "beats",
            "outperform",
            "upgrade",
            "upgrades",
            "surge",
            "surges",
            "soar",
            "soars",
            "positive",
            "optimistic",
            "confidence",
        }
    )

    NEGATIVE_WORDS: frozenset[str] = frozenset(
        {
            "crash",
            "crashes",
            "crashed",
            "fall",
            "falls",
            "fell",
            "drop",
            "drops",
            "dropped",
            "decline",
            "declines",
            "declined",
            "weak",
            "weakly",
            "bearish",
            "miss",
            "misses",
            "underperform",
            "downgrade",
            "downgrades",
            "plunge",
            "plunges",
            "slump",
            "slumps",
            "negative",
            "pessimistic",
            "risk",
            "risks",
            "concern",
            "concerns",
        }
    )

    def analyze(self, text: str) -> SentimentScore:
        """Analyze text and return a SentimentScore.

        Score = (positive_count - negative_count) / total_words, clamped to [-1, 1].
        Neutral text (no keywords) returns 0.
        """
        tokens = text.lower().split()
        total = max(len(tokens), 1)
        pos = sum(1 for t in tokens if t in self.POSITIVE_WORDS)
        neg = sum(1 for t in tokens if t in self.NEGATIVE_WORDS)

        raw = Decimal(pos - neg) / Decimal(total)
        score = max(Decimal(-1), min(Decimal(1), raw))

        return SentimentScore(
            score=score,
            source=NewsSource.RSS_FEED,
            timestamp=datetime.now(UTC),
        )


def analyze_sentiment(text: str) -> SentimentScore:
    """Convenience: analyze text sentiment."""
    return SentimentAnalyzer().analyze(text)


def aggregate_sentiment(symbol: str, scores: list[SentimentScore]) -> SentimentResult:
    """Aggregate multiple sentiment scores for a symbol."""
    if not scores:
        return SentimentResult(
            symbol=symbol,
            average_score=Decimal(0),
            item_count=0,
            latest_timestamp=datetime.now(UTC),
        )

    total = sum((s.score for s in scores), Decimal(0))
    average = total / Decimal(len(scores))
    latest = max(s.timestamp for s in scores)

    return SentimentResult(
        symbol=symbol,
        average_score=average,
        item_count=len(scores),
        latest_timestamp=latest,
    )


def check_pipeline_reliability(
    technical_pipeline_reliable: bool,
    risk_management_active: bool,
    position_management_active: bool,
) -> PipelineReliability:
    """Convenience: build a PipelineReliability."""
    return PipelineReliability(
        technical_pipeline_reliable=technical_pipeline_reliable,
        risk_management_active=risk_management_active,
        position_management_active=position_management_active,
    )


def is_source_permitted(source: NewsSource) -> bool:
    """Return True if the source is a permitted free source."""
    return source in (NewsSource.RSS_FEED, NewsSource.FREE_NEWS_API)
