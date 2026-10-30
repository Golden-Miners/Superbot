# TDD Evidence Report — M10.2 Resource telemetry for API/workers/DB/model/MT5/data/queue

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M10.2` ("Resource telemetry for API/workers/DB/model/MT5/data/queue").

## User journeys
- As a system operator, I want to register resources of types API, WORKER, DB, MODEL, MT5, DATA, QUEUE with an endpoint
- As a system operator, I want to record metrics (cpu_usage, memory_mb, depth, latency, rows_per_second) for each resource with timestamps
- As a system operator, I want point-in-time snapshots showing the latest value per metric for each resource
- As a system operator, I want to list all resource IDs, optionally filtered by resource type
- As a system operator, I want pressure detection when CPU or memory utilization exceeds configurable thresholds
- As a system operator, I want all telemetry decisions deterministic — same inputs → identical results
- Stdlib-only, no import-time network/database activity

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| ResourceType enum | `tests/unit/test_resource_telemetry.py::test_resource_type_enum` | ModuleNotFoundError | PASS | API/WORKER/DB/MODEL/MT5/DATA/QUEUE values |
| ResourceMetric creation | `tests/unit/test_resource_telemetry.py::test_resource_metric_creates` | ModuleNotFoundError | PASS | Stores name, value, unit, timestamp, type, id |
| ResourceSnapshot creation | `tests/unit/test_resource_telemetry.py::test_resource_snapshot_creates` | ModuleNotFoundError | PASS | Stores id, type, metrics, timestamp |
| ResourceRegistry creation | `tests/unit/test_resource_telemetry.py::test_resource_registry_creates` | ModuleNotFoundError | PASS | Instantiates |
| Register resource | `tests/unit/test_resource_telemetry.py::test_register_resource` | ModuleNotFoundError | PASS | Resource stored and retrievable |
| Get unknown resource | `tests/unit/test_resource_telemetry.py::test_get_unknown_resource` | ModuleNotFoundError | PASS | Returns None |
| Record metric | `tests/unit/test_resource_telemetry.py::test_record_metric` | ModuleNotFoundError | PASS | Metric added to history |
| Get snapshot | `tests/unit/test_resource_telemetry.py::test_get_snapshot` | ModuleNotFoundError | PASS | Returns latest metric values |
| TelemetryCollector creation | `tests/unit/test_resource_telemetry.py::test_telemetry_collector_creates` | ModuleNotFoundError | PASS | Instantiates (registry optional) |
| Collect API metric | `tests/unit/test_resource_telemetry.py::test_collect_metric_api` | ModuleNotFoundError | PASS | Metric recorded for known resource |
| Collect unknown resource | `tests/unit/test_resource_telemetry.py::test_collect_metric_unknown_resource` | ModuleNotFoundError | PASS | recorded=False for unknown resource |
| Pressure detects CPU | `tests/unit/test_resource_telemetry.py::test_resource_pressure_detects` | ModuleNotFoundError | PASS | CPU above threshold → under_pressure=True |
| Pressure no pressure | `tests/unit/test_resource_telemetry.py::test_resource_pressure_no_pressure` | ModuleNotFoundError | PASS | Below thresholds → under_pressure=False |
| Pressure memory | `tests/unit/test_resource_telemetry.py::test_resource_pressure_memory` | ModuleNotFoundError | PASS | Memory above threshold → under_pressure=True |
| Pressure deterministic | `tests/unit/test_resource_telemetry.py::test_resource_pressure_deterministic` | ModuleNotFoundError | PASS | Same inputs → identical result |
| Convenience functions | `test_get_resource_pressure_function`, `test_get_snapshot_function`, `test_register_resource_function`, `test_record_metric_function`, `test_collect_metric_function` | ModuleNotFoundError | PASS | Module-level wrappers work |
| List resource IDs | `tests/unit/test_resource_telemetry.py::test_registry_lists_resources` | ModuleNotFoundError | PASS | Returns all registered IDs |
| List by type | `tests/unit/test_resource_telemetry.py::test_registry_resources_by_type` | ModuleNotFoundError | PASS | Filters by resource type |
| Snapshot deterministic | `tests/unit/test_resource_telemetry.py::test_snapshot_deterministic` | ModuleNotFoundError | PASS | Same inputs → identical snapshot |
| Pressure without memory total | `tests/unit/test_resource_telemetry.py::test_pressure_without_memory_total` | ModuleNotFoundError | PASS | Handles missing memory_total_mb |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Resource registration & lookup | `tests/unit/test_resource_telemetry.py` | unit | PASS | 774 passed, 2 skipped |
| 2 | Metric recording & history | `tests/unit/test_resource_telemetry.py` | unit | PASS | 774 passed, 2 skipped |
| 3 | Point-in-time snapshots | `tests/unit/test_resource_telemetry.py` | unit | PASS | 774 passed, 2 skipped |
| 4 | Resource listing (all + by type) | `tests/unit/test_resource_telemetry.py` | unit | PASS | 774 passed, 2 skipped |
| 5 | Pressure detection (CPU/memory) | `tests/unit/test_resource_telemetry.py` | unit | PASS | 774 passed, 2 skipped |
| 6 | Deterministic results | `tests/unit/test_resource_telemetry.py` | unit | PASS | 774 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M10.2 lines exercised by unit tests
- Intentional gap: no persistence — in-memory registry only
- Intentional gap: no background collection loop — metrics recorded on demand
- Intentional gap: pressure detection is rule-based (CPU/memory thresholds), no ML anomaly detection

## Merge evidence
RED: `ModuleNotFoundError: No module named 'superbot.m10.resource_telemetry'` captured before implementation. GREEN: 774 tests pass, 2 skipped, ruff clean, format clean, working tree clean.