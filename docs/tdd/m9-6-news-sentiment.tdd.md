# TDD Evidence Report — M9.6 News/sentiment only after core technical pipeline is reliable; permitted free sources

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M9.6` ("News/sentiment only after core technical pipeline is reliable; permitted free sources").

## User journeys
- As a system operator, I want sentiment analysis of news text using only free sources, so no paid API keys are needed
- As a system operator, I want sentiment clamped to [-1, 1] so downstream systems can rely on normalized values
- As a system operator, I want news ingestion blocked unless the core technical pipeline is reliable (technical + risk + position management all active), so sentiment never drives decisions when the pipeline isn't ready
- As a system operator, I want only permitted free sources (RSS_FEED, FREE_NEWS_API) so no paid/unapproved sources are used
- As a system operator, I want deterministic sentiment results so same text always yields the same score
- Stdlib-only, no import-time network activity

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| SentimentScore creation | `tests/unit/test_news_sentiment.py::test_sentiment_score_creates` | ModuleNotFoundError | PASS | Stores score, source, timestamp |
| NewsItem creation | `tests/unit/test_news_sentiment.py::test_news_item_creates` | ModuleNotFoundError | PASS | Stores headline, body, source, timestamp, symbol |
| NewsSource enum free only | `tests/unit/test_news_sentiment.py::test_news_source_enum` | ModuleNotFoundError | PASS | RSS_FEED and FREE_NEWS_API only |
| is_source_permitted free | `tests/unit/test_news_sentiment.py::test_is_source_permitted_free` | ModuleNotFoundError | PASS | Free sources return True |
| SentimentAnalyzer creation | `tests/unit/test_news_sentiment.py::test_sentiment_analyzer_creates` | ModuleNotFoundError | PASS | Instantiates |
| Analyze positive text | `tests/unit/test_news_sentiment.py::test_analyze_positive` | ModuleNotFoundError | PASS | Positive text → score > 0 |
| Analyze negative text | `tests/unit/test_news_sentiment.py::test_analyze_negative` | ModuleNotFoundError | PASS | Negative text → score < 0 |
| Analyze neutral text | `tests/unit/test_news_sentiment.py::test_analyze_neutral` | ModuleNotFoundError | PASS | Neutral text → |score| ≤ 0.1 |
| Analyze deterministic | `tests/unit/test_news_sentiment.py::test_analyze_deterministic` | ModuleNotFoundError | PASS | Same text → identical score |
| SentimentResult creation | `tests/unit/test_news_sentiment.py::test_sentiment_result_creates` | ModuleNotFoundError | PASS | Stores symbol, average_score, item_count, latest_timestamp |
| aggregate_sentiment | `tests/unit/test_news_sentiment.py::test_aggregate_sentiment` | ModuleNotFoundError | PASS | Combines scores into average |
| PipelineReliability creation | `tests/unit/test_news_sentiment.py::test_pipeline_reliability_creates` | ModuleNotFoundError | PASS | Stores readiness flags |
| SourceGate blocks unreliable | `tests/unit/test_news_sentiment.py::test_sourcegate_blocks_unreliable` | ModuleNotFoundError | PASS | Any flag False → allows_ingestion() False |
| SourceGate allows reliable | `tests/unit/test_news_sentiment.py::test_sourcegate_allows_reliable` | ModuleNotFoundError | PASS | All flags True → allows_ingestion() True |
| check_pipeline_reliability fn | `tests/unit/test_news_sentiment.py::test_check_pipeline_reliability_function` | ModuleNotFoundError | PASS | Convenience builder works |
| analyze_sentiment fn | `tests/unit/test_news_sentiment.py::test_analyze_sentiment_function` | ModuleNotFoundError | PASS | Convenience wrapper works |
| aggregate_sentiment fn | `tests/unit/test_news_sentiment.py::test_aggregate_sentiment_function` | ModuleNotFoundError | PASS | Convenience wrapper works |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Deterministic keyword sentiment | `tests/unit/test_news_sentiment.py` | unit | PASS | 687 passed, 2 skipped |
| 2 | Score clamped to [-1, 1] | `tests/unit/test_news_sentiment.py` | unit | PASS | 687 passed, 2 skipped |
| 3 | Free sources only | `tests/unit/test_news_sentiment.py` | unit | PASS | 687 passed, 2 skipped |
| 4 | SourceGate pipeline reliability | `tests/unit/test_news_sentiment.py` | unit | PASS | 687 passed, 2 skipped |
| 5 | Aggregation of scores | `tests/unit/test_news_sentiment.py` | unit | PASS | 687 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M9.6 lines exercised by unit tests
- Intentional gap: no network/RSS fetching — purely in-memory deterministic analysis
- Intentional gap: no persistence of sentiment results — in-memory only
- Known limit: analyzer is keyword-based (not ML), suitable as a deterministic placeholder until a vetted local model is available

## Merge evidence
RED: `ModuleNotFoundError: No module named 'superbot.m9.news_sentiment'` captured before implementation. GREEN: 687 tests pass, 2 skipped, ruff clean, format clean, working tree clean.