"""RED tests for M2.3 dataset manifest/version/hash and lineage (schema.md section 4).

Dataset ID + content hash must uniquely identify experiment data.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from superbot.data.dataset_manifest import (
    DatasetManifest,
    InvalidDatasetManifestError,
)


def test_valid_dataset_manifest_accepted():
    manifest = DatasetManifest(
        schema_version="1.0.0",
        dataset_id="ds-gold-m5-20261028",
        content_hash="sha256:e94d14955d1ad1a425c58c17be60aaec3904a77fcbb38d458ced86068a6a33bd",
        source_ids=["xm-mt5"],
        coverage={"XAUUSD": ["M5"]},
        start_utc=datetime(2026, 10, 27, 0, 0, tzinfo=UTC),
        end_utc=datetime(2026, 10, 28, 0, 0, tzinfo=UTC),
        bar_count=288,
        bar_schema_version="1.0.0",
        created_at_utc=datetime(2026, 10, 28, 12, 0, tzinfo=UTC),
        updated_at_utc=datetime(2026, 10, 28, 12, 0, tzinfo=UTC),
        acquisition_code_version="abc1234",
        quality_report_ref="qr-001",
        parent_dataset_refs=[],
        excluded_period_refs=[],
        storage_uri="file:///data/datasets/ds-gold-m5-20261028.parquet",
        limitations="Synthetic fixture only; not market data.",
    )
    assert manifest.dataset_id == "ds-gold-m5-20261028"
    assert manifest.coverage == {"XAUUSD": ["M5"]}


def test_dataset_id_and_hash_uniquely_identify_experiment_data():
    m1 = DatasetManifest(
        schema_version="1.0.0",
        dataset_id="ds-a",
        content_hash="hash-a",
        source_ids=["x"],
        coverage={},
        start_utc=datetime(2026, 10, 27, tzinfo=UTC),
        end_utc=datetime(2026, 10, 28, tzinfo=UTC),
        bar_count=1,
        bar_schema_version="1.0.0",
        created_at_utc=datetime(2026, 10, 27, tzinfo=UTC),
        updated_at_utc=datetime(2026, 10, 27, tzinfo=UTC),
        acquisition_code_version="v1",
        quality_report_ref="qr",
        parent_dataset_refs=[],
        excluded_period_refs=[],
        storage_uri="file:///a",
        limitations="",
    )
    m2 = DatasetManifest(
        schema_version="1.0.0",
        dataset_id="ds-b",
        content_hash="hash-b",
        source_ids=["x"],
        coverage={},
        start_utc=datetime(2026, 10, 27, tzinfo=UTC),
        end_utc=datetime(2026, 10, 28, tzinfo=UTC),
        bar_count=1,
        bar_schema_version="1.0.0",
        created_at_utc=datetime(2026, 10, 27, tzinfo=UTC),
        updated_at_utc=datetime(2026, 10, 27, tzinfo=UTC),
        acquisition_code_version="v1",
        quality_report_ref="qr",
        parent_dataset_refs=[],
        excluded_period_refs=[],
        storage_uri="file:///b",
        limitations="",
    )
    assert (m1.dataset_id, m1.content_hash) != (m2.dataset_id, m2.content_hash)


def test_required_fields_rejected_when_missing():
    with pytest.raises(InvalidDatasetManifestError):
        DatasetManifest(
            schema_version="1.0.0",
            dataset_id="",
            content_hash="hash",
            source_ids=["x"],
            coverage={},
            start_utc=datetime(2026, 10, 27, tzinfo=UTC),
            end_utc=datetime(2026, 10, 28, tzinfo=UTC),
            bar_count=1,
            bar_schema_version="1.0.0",
            created_at_utc=datetime(2026, 10, 27, tzinfo=UTC),
            updated_at_utc=datetime(2026, 10, 27, tzinfo=UTC),
            acquisition_code_version="v1",
            quality_report_ref="qr",
            parent_dataset_refs=[],
            excluded_period_refs=[],
            storage_uri="file:///a",
            limitations="",
        )


def test_end_before_start_rejected():
    with pytest.raises(InvalidDatasetManifestError):
        DatasetManifest(
            schema_version="1.0.0",
            dataset_id="ds",
            content_hash="hash",
            source_ids=["x"],
            coverage={},
            start_utc=datetime(2026, 10, 28, tzinfo=UTC),
            end_utc=datetime(2026, 10, 27, tzinfo=UTC),
            bar_count=1,
            bar_schema_version="1.0.0",
            created_at_utc=datetime(2026, 10, 27, tzinfo=UTC),
            updated_at_utc=datetime(2026, 10, 27, tzinfo=UTC),
            acquisition_code_version="v1",
            quality_report_ref="qr",
            parent_dataset_refs=[],
            excluded_period_refs=[],
            storage_uri="file:///a",
            limitations="",
        )
