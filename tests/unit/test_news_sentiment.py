"""RED tests for M9.6 — News/sentiment only after core technical pipeline is reliable; permitted free sources.

Tests define:
- SentimentScore: normalized sentiment value (-1 to 1) with source and timestamp
- NewsItem: a news article with headline, body, source, timestamp, symbol
- SentimentAnalyzer: analyzes text and produces a sentiment score
- NewsSource: enum of permitted free news sources (RSS feeds, etc.)
- SourceGate: blocks news ingestion unless pipeline reliability checks pass
- SentimentResult: aggregated sentiment for a symbol over a window
- Deterministic: same inputs -> identical results
- Only free/no-API-key sources permitted (no paid APIs)
- Stdlib-only, no import-time network activity
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from superbot.m9.news_sentiment import (
    NewsItem,
    NewsSource,
    PipelineReliability,
    SentimentAnalyzer,
    SentimentResult,
    SentimentScore,
    SourceGate,
    aggregate_sentiment,
    analyze_sentiment,
    check_pipeline_reliability,
    is_source_permitted,
)


def test_sentiment_score_creates():
    """SentimentScore stores score, source, timestamp."""
    score = SentimentScore(
        score=Decimal("0.3"),
        source=NewsSource.RSS_FEED,
        timestamp=datetime(2026, 10, 28, 9, 0, 0),
    )
    assert score.score == Decimal("0.3")
    assert score.source == NewsSource.RSS_FEED


def test_news_item_creates():
    """NewsItem stores headline, body, source, timestamp, symbol."""
    item = NewsItem(
        headline="EURUSD rises on rate news",
        body="The euro strengthened after the rate decision.",
        source=NewsSource.RSS_FEED,
        timestamp=datetime(2026, 10, 28, 9, 0, 0),
        symbol="EURUSD",
    )
    assert item.headline == "EURUSD rises on rate news"
    assert item.symbol == "EURUSD"


def test_news_source_enum():
    """NewsSource lists only free permitted sources."""
    assert NewsSource.RSS_FEED.value == "rss_feed"
    assert NewsSource.FREE_NEWS_API.value == "free_news_api"


def test_is_source_permitted_free():
    """is_source_permitted returns True for free sources."""
    assert is_source_permitted(NewsSource.RSS_FEED) is True
    assert is_source_permitted(NewsSource.FREE_NEWS_API) is True


def test_sentiment_analyzer_creates():
    """SentimentAnalyzer can be created."""
    analyzer = SentimentAnalyzer()
    assert analyzer is not None


def test_analyze_positive():
    """Positive text yields score > 0."""
    analyzer = SentimentAnalyzer()
    score = analyzer.analyze("EURUSD rallies strongly on good news")
    assert score.score > Decimal(0)


def test_analyze_negative():
    """Negative text yields score < 0."""
    analyzer = SentimentAnalyzer()
    score = analyzer.analyze("EURUSD crashes badly on terrible news")
    assert score.score < Decimal(0)


def test_analyze_neutral():
    """Neutral text yields score near 0."""
    analyzer = SentimentAnalyzer()
    score = analyzer.analyze("EURUSD trades sideways in a range")
    assert abs(score.score) <= Decimal("0.1")


def test_analyze_deterministic():
    """Same text yields identical scores."""
    a1 = SentimentAnalyzer()
    a2 = SentimentAnalyzer()
    s1 = a1.analyze("EURUSD rallies on rate news")
    s2 = a2.analyze("EURUSD rallies on rate news")
    assert s1.score == s2.score


def test_sentiment_result_creates():
    """SentimentResult stores aggregated metrics."""
    result = SentimentResult(
        symbol="EURUSD",
        average_score=Decimal("0.2"),
        item_count=5,
        latest_timestamp=datetime(2026, 10, 28, 9, 0, 0),
    )
    assert result.symbol == "EURUSD"
    assert result.item_count == 5


def test_aggregate_sentiment():
    """aggregate_sentiment combines multiple scores."""
    scores = [
        SentimentScore(Decimal("0.5"), NewsSource.RSS_FEED, datetime(2026, 10, 28, 9, 0, 0)),
        SentimentScore(Decimal("-0.1"), NewsSource.RSS_FEED, datetime(2026, 10, 28, 9, 5, 0)),
        SentimentScore(Decimal("0.3"), NewsSource.FREE_NEWS_API, datetime(2026, 10, 28, 9, 10, 0)),
    ]
    result = aggregate_sentiment("EURUSD", scores)
    assert result.average_score == Decimal("0.2333333333333333333333333333")
    assert result.item_count == 3


def test_pipeline_reliability_creates():
    """PipelineReliability stores readiness flags."""
    pr = PipelineReliability(
        technical_pipeline_reliable=True,
        risk_management_active=True,
        position_management_active=True,
    )
    assert pr.technical_pipeline_reliable is True


def test_sourcegate_blocks_unreliable():
    """SourceGate blocks news when pipeline unreliable."""
    gate = SourceGate(PipelineReliability(False, True, True))
    assert gate.allows_ingestion() is False


def test_sourcegate_allows_reliable():
    """SourceGate allows news when pipeline reliable."""
    gate = SourceGate(PipelineReliability(True, True, True))
    assert gate.allows_ingestion() is True


def test_check_pipeline_reliability_function():
    """check_pipeline_reliability convenience function works."""
    pr = check_pipeline_reliability(True, True, True)
    assert pr.technical_pipeline_reliable is True


def test_analyze_sentiment_function():
    """analyze_sentiment convenience function works."""
    score = analyze_sentiment("EURUSD rallies strongly")
    assert score.score > Decimal(0)


def test_aggregate_sentiment_function():
    """aggregate_sentiment convenience function works."""
    scores = [SentimentScore(Decimal("0.5"), NewsSource.RSS_FEED, datetime(2026, 10, 28, 9, 0, 0))]
    result = aggregate_sentiment("EURUSD", scores)
    assert result.item_count == 1
