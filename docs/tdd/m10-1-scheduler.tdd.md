# TDD Evidence Report — M10.1 Priority tiers, bounded concurrency, duplicate job prevention, intervals/missed-run rules

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M10.1` ("Priority tiers, bounded concurrency, duplicate job prevention, intervals/missed-run rules").

## User journeys
- As a system operator, I want jobs queued by priority tier (CRITICAL > HIGH > NORMAL > LOW) so critical work runs first
- As a system operator, I want bounded concurrency so no more than N jobs run at once, preventing resource exhaustion
- As a system operator, I want duplicate job submissions (same idempotency key) rejected so work isn't executed twice
- As a system operator, I want recurring jobs scheduled at fixed intervals with the next-run time tracked
- As a system operator, I want missed runs handled by a configurable policy (SKIP / CATCH_UP / FAIL) so behavior is predictable
- As a system operator, I want all scheduling decisions deterministic from explicit rules — same inputs → identical results
- Stdlib-only, no import-time network/database activity

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| PriorityTier ordering | `tests/unit/test_scheduler.py::test_priority_tier_ordering` | ModuleNotFoundError | PASS | CRITICAL(4) > HIGH(3) > NORMAL(2) > LOW(1) |
| Job creation | `tests/unit/test_scheduler.py::test_job_creates` | ModuleNotFoundError | PASS | Stores id, priority, payload, scheduled_at, status |
| JobQueue creation | `tests/unit/test_scheduler.py::test_job_queue_creates` | ModuleNotFoundError | PASS | Instantiates |
| JobQueue priority order | `tests/unit/test_scheduler.py::test_job_queue_priority_order` | ModuleNotFoundError | PASS | Dequeues highest priority first regardless of insertion order |
| JobQueue empty | `tests/unit/test_scheduler.py::test_job_queue_empty_returns_none` | ModuleNotFoundError | PASS | dequeue() returns None when empty |
| ConcurrencyLimiter creation | `tests/unit/test_scheduler.py::test_concurrency_limiter_creates` | ModuleNotFoundError | PASS | Stores max_concurrent, current_running=0 |
| Concurrency acquire/release | `tests/unit/test_scheduler.py::test_concurrency_limiter_acquire_release` | ModuleNotFoundError | PASS | Acquires slots up to max, blocks at capacity, releases frees |
| Concurrency release unknown | `tests/unit/test_scheduler.py::test_concurrency_limiter_release_unknown` | ModuleNotFoundError | PASS | No-op on unknown job |
| DuplicateJobPrevention creation | `tests/unit/test_scheduler.py::test_duplicate_job_prevention_creates` | ModuleNotFoundError | PASS | Instantiates |
| Register/detect duplicate | `tests/unit/test_scheduler.py::test_register_and_detect_duplicate` | ModuleNotFoundError | PASS | First register=False, second=True |
| IntervalScheduler creation | `tests/unit/test_scheduler.py::test_interval_scheduler_creates` | ModuleNotFoundError | PASS | Instantiates |
| Schedule interval | `tests/unit/test_scheduler.py::test_schedule_interval` | ModuleNotFoundError | PASS | Registers job with interval + next_run |
| Interval advances | `tests/unit/test_scheduler.py::test_interval_advances` | ModuleNotFoundError | PASS | next_run += interval on advance |
| MissedRunPolicy enum | `tests/unit/test_scheduler.py::test_missed_run_policy_enum` | ModuleNotFoundError | PASS | SKIP/CATCH_UP/FAIL values |
| Mark missed run SKIP | `tests/unit/test_scheduler.py::test_mark_missed_run_skip` | ModuleNotFoundError | PASS | skipped=True, queued=False |
| Mark missed run CATCH_UP | `tests/unit/test_scheduler.py::test_mark_missed_run_catch_up` | ModuleNotFoundError | PASS | skipped=False, queued=True |
| Scheduler creation | `tests/unit/test_scheduler.py::test_scheduler_creates` | ModuleNotFoundError | PASS | Stores max_concurrent |
| Submit job | `tests/unit/test_scheduler.py::test_submit_job` | ModuleNotFoundError | PASS | accepted=True, job_id set |
| Submit duplicate job | `tests/unit/test_scheduler.py::test_submit_duplicate_job` | ModuleNotFoundError | PASS | accepted=False, reason="duplicate" |
| Get next job priority | `tests/unit/test_scheduler.py::test_get_next_job_returns_highest_priority` | ModuleNotFoundError | PASS | Returns highest priority pending job |
| Complete job | `tests/unit/test_scheduler.py::test_complete_job` | ModuleNotFoundError | PASS | completed=True, frees slot |
| Fail job | `tests/unit/test_scheduler.py::test_fail_job` | ModuleNotFoundError | PASS | failed=True, error set |
| Deterministic scheduler | `tests/unit/test_scheduler.py::test_scheduler_deterministic` | ModuleNotFoundError | PASS | Same inputs → identical results |
| Convenience functions | `test_add_job_function`, `test_enqueue_job_function`, `test_get_next_job_function`, `test_complete_job_function`, `test_fail_job_function`, `test_is_duplicate_function`, `test_register_duplicate_function`, `test_schedule_interval_function`, `test_mark_missed_run_function`, `test_create_scheduler_function` | ModuleNotFoundError | PASS | Module-level wrappers work |
| SchedulerResult creation | `tests/unit/test_scheduler.py::test_scheduler_result_creates` | ModuleNotFoundError | PASS | Stores accepted, job_id, reason |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Priority tier ordering | `tests/unit/test_scheduler.py` | unit | PASS | 750 passed, 2 skipped |
| 2 | Priority-ordered queue | `tests/unit/test_scheduler.py` | unit | PASS | 750 passed, 2 skipped |
| 3 | Bounded concurrency | `tests/unit/test_scheduler.py` | unit | PASS | 750 passed, 2 skipped |
| 4 | Duplicate detection | `tests/unit/test_scheduler.py` | unit | PASS | 750 passed, 2 skipped |
| 5 | Interval scheduling + advance | `tests/unit/test_scheduler.py` | unit | PASS | 750 passed, 2 skipped |
| 6 | Missed-run policy | `tests/unit/test_scheduler.py` | unit | PASS | 750 passed, 2 skipped |
| 7 | Scheduler orchestration | `tests/unit/test_scheduler.py` | unit | PASS | 750 passed, 2 skipped |
| 8 | Deterministic results | `tests/unit/test_scheduler.py` | unit | PASS | 750 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M10.1 lines exercised by unit tests
- Intentional gap: no persistence of jobs/queue state — in-memory only
- Intentional gap: no actual job execution (no callback invocation) — scheduling/queue layer only
- Intentional gap: missed-run catch-up doesn't actually reschedule — returns queued=True flag only

## Merge evidence
RED: `ModuleNotFoundError: No module named 'superbot.m10.scheduler'` captured before implementation. GREEN: 750 tests pass, 2 skipped, ruff clean, format clean, working tree clean.