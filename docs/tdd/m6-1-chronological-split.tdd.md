# TDD Evidence Report — M6.1 Chronological Train/Validation/Test Split

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M6.1` ("Chronological train/validation/untouched-test split and leakage audit").

## User journeys
- As a researcher, I want chronological split: train = earliest bars, validation = middle, test = latest
- As a researcher, I want no overlap between splits (no duplicate timestamps)
- As a researcher, I want gap bars between validation and test to prevent leakage
- As a researcher, I want leakage detection: duplicate bars across splits = leakage error
- As a researcher, I want leakage detection: future-dated data in training = leakage error
- As a researcher, I want minimum split sizes enforced
- As a researcher, I want untouched test set never used in training/validation
- As a researcher, I want deterministic: same inputs → same split
- As a researcher, I want versioned split spec: SplitSpec carries schema_version and spec_id

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| Chronological order | `tests/unit/test_chronological_split.py::test_split_chronological_order` | ModuleNotFoundError | PASS | Train < Val < Test in timestamp order |
| No overlap across splits | `tests/unit/test_chronological_split.py::test_no_overlap_across_splits` | ModuleNotFoundError | PASS | No timestamp in multiple splits |
| Gap between val and test | `tests/unit/test_chronological_split.py::test_gap_between_val_and_test` | ModuleNotFoundError | PASS | Gap bars separate val from test |
| Insufficient bars raises | `tests/unit/test_chronological_split.py::test_insufficient_bars_raises` | ModuleNotFoundError | PASS | ValueError when bars < required |
| Minimum split sizes | `tests/unit/test_chronological_split.py::test_minimum_split_sizes` | ModuleNotFoundError | PASS | Each split meets its minimum size |
| Untouched test set | `tests/unit/test_chronological_split.py::test_untouched_test_not_in_training` | ModuleNotFoundError | PASS | Test set never in training/validation |
| Deterministic split | `tests/unit/test_chronological_split.py::test_deterministic_split` | ModuleNotFoundError | PASS | Same inputs → identical split |
| Audit: no overlap passes | `tests/unit/test_chronological_split.py::test_audit_leakage_no_overlap_passes` | ModuleNotFoundError | PASS | Clean split passes audit |
| Audit: duplicate across splits | `tests/unit/test_chronological_split.py::test_audit_leakage_duplicate_across_splits` | ModuleNotFoundError | PASS | Duplicate timestamp raises LeakageError |
| Audit: future data in train | `tests/unit/test_chronological_split.py::test_audit_leakage_future_data_in_train` | ModuleNotFoundError | PASS | Future data in train raises LeakageError |
| SplitSpec versioned | `tests/unit/test_chronological_split.py::test_split_spec_versioned` | ModuleNotFoundError | PASS | schema_version + spec_id stored |
| is_chronological ordered | `tests/unit/test_chronological_split.py::test_is_chronological_ordered` | ModuleNotFoundError | PASS | Ascending timestamps = chronological |
| is_chronological unordered | `tests/unit/test_chronological_split.py::test_is_chronological_unordered` | ModuleNotFoundError | PASS | Unordered timestamps = not chronological |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Train < Val < Test order | `tests/unit/test_chronological_split.py` | unit | PASS | 253 passed, 2 skipped |
| 2 | No overlap across splits | `tests/unit/test_chronological_split.py` | unit | PASS | 253 passed, 2 skipped |
| 3 | Gap between val and test | `tests/unit/test_chronological_split.py` | unit | PASS | 253 passed, 2 skipped |
| 4 | Insufficient bars rejected | `tests/unit/test_chronological_split.py` | unit | PASS | 253 passed, 2 skipped |
| 5 | Minimum split sizes met | `tests/unit/test_chronological_split.py` | unit | PASS | 253 passed, 2 skipped |
| 6 | Test set untouched | `tests/unit/test_chronological_split.py` | unit | PASS | 253 passed, 2 skipped |
| 7 | Deterministic split | `tests/unit/test_chronological_split.py` | unit | PASS | 253 passed, 2 skipped |
| 8 | Leakage: duplicates detected | `tests/unit/test_chronological_split.py` | unit | PASS | 253 passed, 2 skipped |
| 9 | Leakage: future data detected | `tests/unit/test_chronological_split.py` | unit | PASS | 253 passed, 2 skipped |
| 10 | is_chronological check | `tests/unit/test_chronological_split.py` | unit | PASS | 253 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M6.1 lines exercised by unit tests
- Intentional gap: split_spec parameter ratios not supported — only absolute bar counts
- Intentional gap: no persistence of split results to disk — in-memory only
- Intentional gap: no feature-level leakage audit (e.g., features computed from future data) — only timestamp-level
- Gap bars are excluded from all splits (not assigned to train/val/test)

## Merge evidence
Commit: `f93851b` (M5.5) + M6.1 commit (chronological_split.py + test_chronological_split.py). RED evidence: `ModuleNotFoundError` captured before implementation (`superbot.data.chronological_split` missing). GREEN evidence: 253 tests pass, 2 skipped, ruff clean, format clean, `git diff --check` clean, working tree clean.
