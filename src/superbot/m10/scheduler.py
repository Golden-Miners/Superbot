"""M10.1 — Priority tiers, bounded concurrency, duplicate job prevention, intervals/missed-run rules.

Deterministic scheduler service:
- PriorityTier: CRITICAL, HIGH, NORMAL, LOW
- Job: id, priority, payload, scheduled_at, status (pending/running/completed/failed/skipped)
- JobQueue: priority-ordered heap queue; higher priority dequeued first
- ConcurrencyLimiter: bounds number of concurrently running jobs
- DuplicateJobPrevention: dedupe jobs by idempotency key
- IntervalScheduler: recurring jobs at fixed intervals
- MissedRunPolicy: SKIP / CATCH_UP / FAIL for missed runs
- Scheduler: orchestrates queue + concurrency + dedupe + intervals + missed-run policy
- Stdlib-only; no import-time network/database activity.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class PriorityTier(Enum):
    """Job priority tiers; higher numeric value = higher priority."""

    CRITICAL = 4
    HIGH = 3
    NORMAL = 2
    LOW = 1

    def rank(self) -> int:
        """Return numeric rank for ordering (higher = more important)."""
        return self.value


@dataclass(frozen=True)
class Job:
    """A schedulable unit of work."""

    job_id: str
    priority: PriorityTier
    payload: dict
    scheduled_at: datetime
    status: str = "pending"  # pending, running, completed, failed, skipped


@dataclass(frozen=True)
class SchedulerResult:
    """Result of a scheduler operation."""

    accepted: bool = False
    job_id: str | None = None
    reason: str | None = None
    completed: bool = False
    failed: bool = False
    error: str | None = None
    skipped: bool = False
    queued: bool = False
    enqueued: bool = False
    scheduled: bool = False
    is_duplicate: bool = False


class JobQueue:
    """Priority-ordered job queue using a heap."""

    def __init__(self) -> None:
        self._heap: list[tuple[int, int, Job]] = []
        self._counter = 0  # tie-breaker for equal priority

    def enqueue(self, job: Job) -> None:
        """Add a job to the queue."""
        heapq.heappush(
            self._heap,
            (-job.priority.rank(), self._counter, job),
        )
        self._counter += 1

    def dequeue(self) -> Job | None:
        """Remove and return the highest priority job, or None if empty."""
        if not self._heap:
            return None
        _, _, job = heapq.heappop(self._heap)
        return job

    def __len__(self) -> int:
        return len(self._heap)


class ConcurrencyLimiter:
    """Bounds the number of concurrently running jobs."""

    def __init__(self, max_concurrent: int) -> None:
        self.max_concurrent = max_concurrent
        self._running: set[str] = set()

    @property
    def current_running(self) -> int:
        return len(self._running)

    def acquire(self, job_id: str) -> bool:
        """Try to acquire a concurrency slot for a job."""
        if job_id in self._running:
            return False
        if len(self._running) >= self.max_concurrent:
            return False
        self._running.add(job_id)
        return True

    def release(self, job_id: str) -> None:
        """Release a concurrency slot for a job (no-op if unknown)."""
        self._running.discard(job_id)


class DuplicateJobPrevention:
    """Detects duplicate job submissions by idempotency key."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def register(self, idempotency_key: str) -> bool:
        """Register a key. Returns True if it was already seen (duplicate)."""
        if idempotency_key in self._seen:
            return True
        self._seen.add(idempotency_key)
        return False

    def is_duplicate(self, idempotency_key: str) -> bool:
        """Return True if the key has been seen before."""
        return idempotency_key in self._seen


class MissedRunPolicy(str, Enum):
    """Policy for handling missed scheduled runs."""

    SKIP = "skip"
    CATCH_UP = "catch_up"
    FAIL = "fail"


class IntervalScheduler:
    """Schedules recurring jobs at fixed intervals."""

    def __init__(self) -> None:
        self._schedules: dict[str, tuple] = {}  # job_id -> (interval, next_run)

    def schedule_interval(self, job_id: str, interval: object, next_run: datetime) -> None:
        """Register a recurring job with its interval and first run time."""
        self._schedules[job_id] = (interval, next_run)

    def get_next_run(self, job_id: str) -> datetime | None:
        """Return the next scheduled run time for a job, or None."""
        entry = self._schedules.get(job_id)
        if entry is None:
            return None
        return entry[1]

    def advance(self, job_id: str) -> None:
        """Advance the next run time by one interval."""
        entry = self._schedules.get(job_id)
        if entry is None:
            return
        interval, next_run = entry
        self._schedules[job_id] = (interval, next_run + interval)

    def mark_missed_run(self, job_id: str, policy: MissedRunPolicy) -> SchedulerResult:
        """Mark a missed run with the given policy."""
        if policy == MissedRunPolicy.SKIP:
            return SchedulerResult(skipped=True, job_id=job_id)
        if policy == MissedRunPolicy.CATCH_UP:
            return SchedulerResult(skipped=False, queued=True, job_id=job_id)
        # FAIL
        return SchedulerResult(skipped=False, queued=False, job_id=job_id)


class Scheduler:
    """Orchestrates priority queue, concurrency, dedupe, intervals, missed-run policy."""

    def __init__(self, max_concurrent: int) -> None:
        self.max_concurrent = max_concurrent
        self.queue = JobQueue()
        self.limiter = ConcurrencyLimiter(max_concurrent)
        self.dedup = DuplicateJobPrevention()
        self.intervals = IntervalScheduler()
        self._jobs: dict[str, Job] = {}

    def submit_job(
        self,
        job_id: str,
        priority: PriorityTier,
        payload: dict,
        idempotency_key: str | None = None,
    ) -> SchedulerResult:
        """Submit a job to the queue. Returns SchedulerResult."""
        if idempotency_key is not None and self.dedup.is_duplicate(idempotency_key):
            return SchedulerResult(accepted=False, job_id=job_id, reason="duplicate")
        if idempotency_key is not None:
            self.dedup.register(idempotency_key)
        job = Job(job_id, priority, dict(payload), datetime.now(), "pending")
        self._jobs[job_id] = job
        self.queue.enqueue(job)
        return SchedulerResult(accepted=True, job_id=job_id, reason=None)

    def get_next_job(self) -> Job | None:
        """Return the highest priority pending job (without removing from queue)."""
        # Peek: dequeue and re-enqueue if we can't run it due to concurrency.
        job = self.queue.dequeue()
        if job is None:
            return None
        if self.limiter.acquire(job.job_id):
            job = Job(job.job_id, job.priority, job.payload, job.scheduled_at, "running")
            self._jobs[job.job_id] = job
            return job
        # At capacity — put it back.
        self.queue.enqueue(job)
        return None

    def complete_job(self, job_id: str) -> SchedulerResult:
        """Mark a job completed and free its concurrency slot."""
        self.limiter.release(job_id)
        if job_id in self._jobs:
            self._jobs[job_id] = Job(
                self._jobs[job_id].job_id,
                self._jobs[job_id].priority,
                self._jobs[job_id].payload,
                self._jobs[job_id].scheduled_at,
                "completed",
            )
        return SchedulerResult(completed=True, job_id=job_id)

    def fail_job(self, job_id: str, error: str) -> SchedulerResult:
        """Mark a job failed and free its concurrency slot."""
        self.limiter.release(job_id)
        if job_id in self._jobs:
            self._jobs[job_id] = Job(
                self._jobs[job_id].job_id,
                self._jobs[job_id].priority,
                self._jobs[job_id].payload,
                self._jobs[job_id].scheduled_at,
                "failed",
            )
        return SchedulerResult(failed=True, job_id=job_id, error=error)

    def get_job(self, job_id: str) -> Job | None:
        """Return a job by its ID, or None if not found."""
        return self._jobs.get(job_id)

    def get_jobs(self) -> dict[str, Job]:
        """Return all jobs as a read-only dict copy."""
        return dict(self._jobs)

    def cancel_job(self, job_id: str, confirm_destructive: bool = False) -> SchedulerResult | None:
        """Cancel a job cooperatively.

        If the job is not checkpointed and confirm_destructive is False,
        returns a SchedulerResult indicating the cancel is blocked.
        Otherwise transitions the job to CANCEL_REQUESTED.
        Returns None if the job is not found.
        """
        job = self._jobs.get(job_id)
        if job is None:
            return None
        if not job.payload.get("checkpointed", False) and not confirm_destructive:
            return SchedulerResult(
                accepted=False,
                job_id=job_id,
                reason="uncheckpointed work could be lost; confirm destructive cancellation",
            )
        self._jobs[job_id] = Job(
            job.job_id,
            job.priority,
            job.payload,
            job.scheduled_at,
            "cancel_requested",
        )
        return SchedulerResult(
            accepted=True,
            job_id=job_id,
            reason="cancellation requested; cooperative cancel pending",
        )


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


def create_scheduler(max_concurrent: int) -> Scheduler:
    """Create a Scheduler with the given concurrency limit."""
    return Scheduler(max_concurrent=max_concurrent)


def add_job(
    job_id: str,
    priority: PriorityTier,
    payload: dict,
    max_concurrent: int = 5,
    idempotency_key: str | None = None,
) -> SchedulerResult:
    """Convenience: create a scheduler and submit a job."""
    return create_scheduler(max_concurrent).submit_job(job_id, priority, payload, idempotency_key)


def enqueue_job(queue: JobQueue, job: Job) -> SchedulerResult:
    """Convenience: enqueue a job into a queue."""
    queue.enqueue(job)
    return SchedulerResult(enqueued=True, job_id=job.job_id)


def get_next_job(queue: JobQueue) -> Job | None:
    """Convenience: dequeue the next job from a queue."""
    return queue.dequeue()


def complete_job(scheduler: Scheduler, job_id: str) -> SchedulerResult:
    """Convenience: complete a job on a scheduler."""
    return scheduler.complete_job(job_id)


def fail_job(scheduler: Scheduler, job_id: str, error: str) -> SchedulerResult:
    """Convenience: fail a job on a scheduler."""
    return scheduler.fail_job(job_id, error)


def is_duplicate(dedup: DuplicateJobPrevention, idempotency_key: str) -> bool:
    """Convenience: check if a key is a duplicate."""
    return dedup.is_duplicate(idempotency_key)


def register_duplicate(dedup: DuplicateJobPrevention, idempotency_key: str) -> SchedulerResult:
    """Convenience: register a key; returns whether it was a duplicate."""
    is_dup = dedup.register(idempotency_key)
    return SchedulerResult(is_duplicate=is_dup)


def schedule_interval(
    sched: IntervalScheduler,
    job_id: str,
    interval: object,
    next_run: datetime,
) -> SchedulerResult:
    """Convenience: schedule an interval job."""
    sched.schedule_interval(job_id, interval, next_run)
    return SchedulerResult(scheduled=True, job_id=job_id)


def mark_missed_run(
    sched: IntervalScheduler,
    job_id: str,
    policy: MissedRunPolicy,
) -> SchedulerResult:
    """Convenience: mark a missed run with the given policy."""
    if policy == MissedRunPolicy.SKIP:
        return SchedulerResult(skipped=True, job_id=job_id)
    if policy == MissedRunPolicy.CATCH_UP:
        return SchedulerResult(skipped=False, queued=True, job_id=job_id)
    # FAIL
    return SchedulerResult(skipped=False, queued=False, job_id=job_id)


def submit_job(
    scheduler: Scheduler,
    job_id: str,
    priority: PriorityTier,
    payload: dict,
    idempotency_key: str | None = None,
) -> SchedulerResult:
    """Convenience: submit a job on a scheduler."""
    return scheduler.submit_job(job_id, priority, payload, idempotency_key)
