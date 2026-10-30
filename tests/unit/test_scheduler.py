"""RED tests for M10.1 — Priority tiers, bounded concurrency, duplicate job prevention, intervals/missed-run rules.

Tests define:
- PriorityTier: CRITICAL, HIGH, NORMAL, LOW
- Job: id, priority, payload, scheduled_at, status (pending/running/completed/failed/skipped)
- JobQueue: priority-ordered queue; higher priority dequeued first
- ConcurrencyLimiter: bounds number of concurrently running jobs
- DuplicateJobPrevention: dedupe jobs by idempotency key; second submission returns existing
- IntervalScheduler: schedules recurring jobs at fixed intervals
- MissedRunPolicy: SKIP / CATCH_UP / FAIL for missed runs
- Scheduler: orchestrates queue + concurrency + dedupe + intervals + missed-run policy
- Deterministic: same inputs -> identical results
- Stdlib-only, no import-time network/database activity
"""

from __future__ import annotations

from datetime import datetime, timedelta

from superbot.m10.scheduler import (
    ConcurrencyLimiter,
    DuplicateJobPrevention,
    IntervalScheduler,
    Job,
    JobQueue,
    MissedRunPolicy,
    PriorityTier,
    Scheduler,
    SchedulerResult,
    add_job,
    complete_job,
    create_scheduler,
    enqueue_job,
    fail_job,
    get_next_job,
    is_duplicate,
    mark_missed_run,
    register_duplicate,
    schedule_interval,
)


def test_priority_tier_ordering():
    """PriorityTier values order correctly: CRITICAL > HIGH > NORMAL > LOW."""
    assert PriorityTier.CRITICAL.value > PriorityTier.HIGH.value
    assert PriorityTier.HIGH.value > PriorityTier.NORMAL.value
    assert PriorityTier.NORMAL.value > PriorityTier.LOW.value


def test_job_creates():
    """Job stores id, priority, payload, scheduled_at, status."""
    job = Job(
        job_id="job_1",
        priority=PriorityTier.HIGH,
        payload={"symbol": "EURUSD", "action": "backtest"},
        scheduled_at=datetime(2026, 10, 28, 9, 0, 0),
        status="pending",
    )
    assert job.job_id == "job_1"
    assert job.priority == PriorityTier.HIGH
    assert job.status == "pending"


def test_job_queue_creates():
    """JobQueue can be created."""
    queue = JobQueue()
    assert queue is not None


def test_job_queue_priority_order():
    """JobQueue dequeues highest priority first regardless of insertion order."""
    queue = JobQueue()
    queue.enqueue(Job("j_low", PriorityTier.LOW, {}, datetime(2026, 10, 28, 9, 0, 0), "pending"))
    queue.enqueue(
        Job("j_crit", PriorityTier.CRITICAL, {}, datetime(2026, 10, 28, 9, 0, 0), "pending")
    )
    queue.enqueue(
        Job("j_norm", PriorityTier.NORMAL, {}, datetime(2026, 10, 28, 9, 0, 0), "pending")
    )
    queue.enqueue(Job("j_high", PriorityTier.HIGH, {}, datetime(2026, 10, 28, 9, 0, 0), "pending"))

    first = queue.dequeue()
    assert first.job_id == "j_crit"
    second = queue.dequeue()
    assert second.job_id == "j_high"
    third = queue.dequeue()
    assert third.job_id == "j_norm"
    fourth = queue.dequeue()
    assert fourth.job_id == "j_low"


def test_job_queue_empty_returns_none():
    """JobQueue.dequeue returns None when empty."""
    queue = JobQueue()
    assert queue.dequeue() is None


def test_concurrency_limiter_creates():
    """ConcurrencyLimiter bounds concurrent executions."""
    limiter = ConcurrencyLimiter(max_concurrent=3)
    assert limiter.max_concurrent == 3
    assert limiter.current_running == 0


def test_concurrency_limiter_acquire_release():
    """ConcurrencyLimiter acquires and releases slots."""
    limiter = ConcurrencyLimiter(max_concurrent=2)
    assert limiter.acquire("job_1") is True
    assert limiter.current_running == 1
    assert limiter.acquire("job_2") is True
    assert limiter.current_running == 2
    assert limiter.acquire("job_3") is False  # at capacity
    limiter.release("job_1")
    assert limiter.current_running == 1
    assert limiter.acquire("job_3") is True
    assert limiter.current_running == 2


def test_concurrency_limiter_release_unknown():
    """ConcurrencyLimiter.release on unknown job is a no-op."""
    limiter = ConcurrencyLimiter(max_concurrent=2)
    limiter.release("nonexistent")  # should not raise


def test_duplicate_job_prevention_creates():
    """DuplicateJobPrevention can be created."""
    dedup = DuplicateJobPrevention()
    assert dedup is not None


def test_register_and_detect_duplicate():
    """DuplicateJobPrevention registers a key and detects duplicates."""
    dedup = DuplicateJobPrevention()
    assert dedup.register("job_key_1") is False  # first time, not a duplicate
    assert dedup.register("job_key_1") is True  # second time, duplicate
    assert dedup.is_duplicate("job_key_1") is True
    assert dedup.is_duplicate("job_key_2") is False


def test_interval_scheduler_creates():
    """IntervalScheduler can be created."""
    sched = IntervalScheduler()
    assert sched is not None


def test_schedule_interval():
    """schedule_interval registers a recurring job."""
    sched = IntervalScheduler()
    next_run = datetime(2026, 10, 28, 9, 0, 0)
    sched.schedule_interval("job_interval_1", timedelta(minutes=5), next_run)
    assert sched.get_next_run("job_interval_1") == next_run


def test_interval_advances():
    """IntervalScheduler advances next_run by the interval."""
    sched = IntervalScheduler()
    next_run = datetime(2026, 10, 28, 9, 0, 0)
    sched.schedule_interval("job_interval_1", timedelta(minutes=5), next_run)
    sched.advance("job_interval_1")
    assert sched.get_next_run("job_interval_1") == next_run + timedelta(minutes=5)


def test_missed_run_policy_enum():
    """MissedRunPolicy has SKIP, CATCH_UP, FAIL values."""
    assert MissedRunPolicy.SKIP.value == "skip"
    assert MissedRunPolicy.CATCH_UP.value == "catch_up"
    assert MissedRunPolicy.FAIL.value == "fail"


def test_mark_missed_run_skip():
    """mark_missed_run with SKIP policy does not queue a catch-up job."""
    sched = IntervalScheduler()
    result = sched.mark_missed_run("job_interval_1", MissedRunPolicy.SKIP)
    assert result.skipped is True
    assert result.queued is False


def test_mark_missed_run_catch_up():
    """mark_missed_run with CATCH_UP policy queues a catch-up job."""
    sched = IntervalScheduler()
    result = sched.mark_missed_run("job_interval_1", MissedRunPolicy.CATCH_UP)
    assert result.skipped is False
    assert result.queued is True


def test_scheduler_creates():
    """Scheduler can be created with concurrency and dedupe."""
    sched = Scheduler(max_concurrent=5)
    assert sched.max_concurrent == 5


def test_submit_job():
    """submit_job adds a job to the queue and returns a result."""
    sched = Scheduler(max_concurrent=5)
    result = sched.submit_job("job_1", PriorityTier.NORMAL, {"action": "test"})
    assert result.accepted is True
    assert result.job_id == "job_1"


def test_submit_duplicate_job():
    """submit_job rejects a duplicate idempotency key."""
    sched = Scheduler(max_concurrent=5)
    sched.submit_job("job_1", PriorityTier.NORMAL, {"action": "test"}, idempotency_key="key_1")
    result = sched.submit_job(
        "job_2", PriorityTier.NORMAL, {"action": "test"}, idempotency_key="key_1"
    )
    assert result.accepted is False
    assert result.reason == "duplicate"


def test_get_next_job_returns_highest_priority():
    """get_next_job returns the highest priority pending job."""
    sched = Scheduler(max_concurrent=5)
    sched.submit_job("j_low", PriorityTier.LOW, {})
    sched.submit_job("j_crit", PriorityTier.CRITICAL, {})
    job = sched.get_next_job()
    assert job is not None
    assert job.job_id == "j_crit"


def test_complete_job():
    """complete_job marks a job completed and frees concurrency slot."""
    sched = Scheduler(max_concurrent=2)
    sched.submit_job("job_1", PriorityTier.NORMAL, {})
    job = sched.get_next_job()
    assert job is not None
    result = sched.complete_job("job_1")
    assert result.completed is True


def test_fail_job():
    """fail_job marks a job failed."""
    sched = Scheduler(max_concurrent=2)
    sched.submit_job("job_1", PriorityTier.NORMAL, {})
    job = sched.get_next_job()
    assert job is not None
    result = sched.fail_job("job_1", "boom")
    assert result.failed is True
    assert result.error == "boom"


def test_scheduler_deterministic():
    """Same inputs yield identical scheduling results."""
    s1 = Scheduler(max_concurrent=3)
    s2 = Scheduler(max_concurrent=3)
    s1.submit_job("j_a", PriorityTier.NORMAL, {})
    s1.submit_job("j_b", PriorityTier.CRITICAL, {})
    s2.submit_job("j_a", PriorityTier.NORMAL, {})
    s2.submit_job("j_b", PriorityTier.CRITICAL, {})
    r1 = s1.get_next_job()
    r2 = s2.get_next_job()
    assert r1.job_id == r2.job_id
    assert r1.priority == r2.priority


def test_add_job_function():
    """add_job convenience function works."""
    result = add_job("job_1", PriorityTier.HIGH, {"action": "x"}, max_concurrent=5)
    assert result.accepted is True


def test_enqueue_job_function():
    """enqueue_job convenience function works."""
    queue = JobQueue()
    job = Job("j_1", PriorityTier.NORMAL, {}, datetime(2026, 10, 28, 9, 0, 0), "pending")
    result = enqueue_job(queue, job)
    assert result.enqueued is True


def test_get_next_job_function():
    """get_next_job convenience function works."""
    queue = JobQueue()
    queue.enqueue(Job("j_1", PriorityTier.LOW, {}, datetime(2026, 10, 28, 9, 0, 0), "pending"))
    job = get_next_job(queue)
    assert job is not None
    assert job.job_id == "j_1"


def test_complete_job_function():
    """complete_job convenience function works."""
    sched = Scheduler(max_concurrent=2)
    sched.submit_job("job_1", PriorityTier.NORMAL, {})
    result = complete_job(sched, "job_1")
    assert result.completed is True


def test_fail_job_function():
    """fail_job convenience function works."""
    sched = Scheduler(max_concurrent=2)
    sched.submit_job("job_1", PriorityTier.NORMAL, {})
    result = fail_job(sched, "job_1", "error")
    assert result.failed is True


def test_is_duplicate_function():
    """is_duplicate convenience function works."""
    dedup = DuplicateJobPrevention()
    dedup.register("key_1")
    assert is_duplicate(dedup, "key_1") is True


def test_register_duplicate_function():
    """register_duplicate convenience function works."""
    dedup = DuplicateJobPrevention()
    result = register_duplicate(dedup, "key_1")
    assert result.is_duplicate is False


def test_schedule_interval_function():
    """schedule_interval convenience function works."""
    sched = IntervalScheduler()
    next_run = datetime(2026, 10, 28, 9, 0, 0)
    result = schedule_interval(sched, "job_1", timedelta(minutes=5), next_run)
    assert result.scheduled is True


def test_mark_missed_run_function():
    """mark_missed_run convenience function works."""
    sched = IntervalScheduler()
    result = mark_missed_run(sched, "job_1", MissedRunPolicy.SKIP)
    assert result.skipped is True


def test_create_scheduler_function():
    """create_scheduler convenience function works."""
    sched = create_scheduler(max_concurrent=4)
    assert sched.max_concurrent == 4


def test_scheduler_result_creates():
    """SchedulerResult stores accepted, job_id, reason."""
    result = SchedulerResult(accepted=True, job_id="job_1", reason=None)
    assert result.accepted is True
    assert result.job_id == "job_1"
    assert result.reason is None
