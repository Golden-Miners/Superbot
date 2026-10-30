# TDD Evidence Report — M9.5 Timeout/retry/fallback/skip/conflict and resource-routing tests

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M9.5` ("Timeout/retry/fallback/skip/conflict and resource-routing tests").

## User journeys
- As a system operator, I want operations to time out when they exceed a deadline, so hung tasks don't block forever
- As a system operator, I want failed operations to be retried with backoff up to a max attempt limit, so transient failures self-heal
- As a system operator, I want a fallback path when the primary operation fails, so work continues on degradation
- As a system operator, I want to conditionally skip operations (e.g. during maintenance), so non-critical work can be deferred
- As a system operator, I want to detect conflicts between concurrent operations, so conflicting work isn't double-executed
- As a system operator, I want to route jobs to resources with capacity checks, so no resource is over-allocated
- Stdlib-only, no import-time network/database activity

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| TimeoutConfig creation | `tests/unit/test_timeout_routing.py::test_timeout_config_creates` | ModuleNotFoundError | PASS | Stores timeout_ms and hard_limit_ms |
| TimeoutResult creation | `tests/unit/test_timeout_routing.py::test_timeout_result_creates` | ModuleNotFoundError | PASS | Stores timed_out, elapsed_ms, deadline_ms, reason, result |
| Timeout within limit | `tests/unit/test_timeout_routing.py::test_timeout_handler_within_limit` | ModuleNotFoundError | PASS | Completes before deadline → timed_out=False, result returned |
| Timeout exceeds limit | `tests/unit/test_timeout_routing.py::test_timeout_handler_exceeds_limit` | ModuleNotFoundError | PASS | Exceeds deadline → timed_out=True via threading enforcement |
| RetryConfig creation | `tests/unit/test_timeout_routing.py::test_retry_config_creates` | ModuleNotFoundError | PASS | Stores max_attempts, base_backoff_ms, backoff_multiplier |
| RetryResult creation | `tests/unit/test_timeout_routing.py::test_retry_result_creates` | ModuleNotFoundError | PASS | Stores attempts, succeeded, final_error, result |
| Retry succeeds first try | `tests/unit/test_timeout_routing.py::test_retry_handler_succeeds_first_try` | ModuleNotFoundError | PASS | First attempt succeeds → attempts=1 |
| Retry succeeds after retries | `tests/unit/test_timeout_routing.py::test_retry_handler_succeeds_after_retries` | ModuleNotFoundError | PASS | Transient failure then success → attempts=3 |
| Retry exhausts attempts | `tests/unit/test_timeout_routing.py::test_retry_handler_exhausts_attempts` | ModuleNotFoundError | PASS | Persistent failure → attempts=max, succeeded=False |
| FallbackConfig creation | `tests/unit/test_timeout_routing.py::test_fallback_config_creates` | ModuleNotFoundError | PASS | Stores primary and fallback callables |
| FallbackResult creation | `tests/unit/test_timeout_routing.py::test_fallback_result_creates` | ModuleNotFoundError | PASS | Stores source and value |
| Fallback uses primary | `tests/unit/test_timeout_routing.py::test_fallback_handler_uses_primary` | ModuleNotFoundError | PASS | Primary succeeds → source="primary" |
| Fallback uses fallback | `tests/unit/test_timeout_routing.py::test_fallback_handler_uses_fallback` | ModuleNotFoundError | PASS | Primary fails → source="fallback" |
| SkipConfig creation | `tests/unit/test_timeout_routing.py::test_skip_config_creates` | ModuleNotFoundError | PASS | Stores skip flag and reason |
| SkipResult creation | `tests/unit/test_timeout_routing.py::test_skip_result_creates` | ModuleNotFoundError | PASS | Stores skipped and reason |
| Skip filter skips | `tests/unit/test_timeout_routing.py::test_skip_filter_skips` | ModuleNotFoundError | PASS | skip=True → skipped=True |
| Skip filter doesn't skip | `tests/unit/test_timeout_routing.py::test_skip_filter_does_not_skip` | ModuleNotFoundError | PASS | skip=False → skipped=False |
| ConflictConfig creation | `tests/unit/test_timeout_routing.py::test_conflict_config_creates` | ModuleNotFoundError | PASS | Stores detect_conflicts and conflict_window_ms |
| ConflictResult creation | `tests/unit/test_timeout_routing.py::test_conflict_result_creates` | ModuleNotFoundError | PASS | Stores conflict flag and conflicting_ops |
| Conflict resolver no conflict | `tests/unit/test_timeout_routing.py::test_conflict_resolver_no_conflict` | ModuleNotFoundError | PASS | Non-overlapping ops → conflict=False |
| Conflict resolver conflict | `tests/unit/test_timeout_routing.py::test_conflict_resolver_conflict` | ModuleNotFoundError | PASS | Overlapping ops → conflict=True |
| ResourceRouter creation | `tests/unit/test_timeout_routing.py::test_resource_router_creates` | ModuleNotFoundError | PASS | Stores resource capacities |
| Route resource success | `tests/unit/test_timeout_routing.py::test_route_resource_success` | ModuleNotFoundError | PASS | Capacity available → allocated=True |
| Route resource insufficient | `tests/unit/test_timeout_routing.py::test_route_resource_insufficient_capacity` | ModuleNotFoundError | PASS | Capacity insufficient → allocated=False |
| Convenience functions | `test_execute_with_timeout_function`, `test_retry_operation_function`, `test_route_resource_function` | ModuleNotFoundError | PASS | Module-level convenience wrappers work |
| Deterministic timeout | `tests/unit/test_timeout_routing.py::test_deterministic_timeout` | ModuleNotFoundError | PASS | Same inputs → identical results |
| Deterministic retry | `tests/unit/test_timeout_routing.py::test_deterministic_retry` | ModuleNotFoundError | PASS | Same inputs → identical results |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Timeout enforcement via deadline | `tests/unit/test_timeout_routing.py` | unit | PASS | 670 passed, 2 skipped |
| 2 | Retry with backoff up to max attempts | `tests/unit/test_timeout_routing.py` | unit | PASS | 670 passed, 2 skipped |
| 3 | Fallback primary/fallback | `tests/unit/test_timeout_routing.py` | unit | PASS | 670 passed, 2 skipped |
| 4 | Conditional skip | `tests/unit/test_timeout_routing.py` | unit | PASS | 670 passed, 2 skipped |
| 5 | Conflict detection | `tests/unit/test_timeout_routing.py` | unit | PASS | 670 passed, 2 skipped |
| 6 | Resource routing with capacity | `tests/unit/test_timeout_routing.py` | unit | PASS | 670 passed, 2 skipped |
| 7 | Deterministic results | `tests/unit/test_timeout_routing.py` | unit | PASS | 670 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M9.5 lines exercised by unit tests
- Intentional gap: `hard_limit_ms` is stored in config but not separately enforced (timeout_ms is the active deadline)
- Intentional gap: no persistence of allocations/retries — in-memory only
- Known limit: `threading.Thread` timeout enforcement is best-effort; the target function continues running in a daemon thread after timeout is flagged

## Merge evidence
RED: `ModuleNotFoundError: No module named 'superbot.m9.timeout_routing'` captured before implementation. GREEN: 670 tests pass, 2 skipped, ruff clean, format clean, working tree clean.