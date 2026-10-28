"""Dataset manifest contract (schema.md section 4).

Dataset ID + content hash uniquely identify experiment data for lineage and
reproducibility. No field is silently defaulted or guessed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


class InvalidDatasetManifestError(ValueError):
    """Raised when a dataset manifest fails validation."""


@dataclass(frozen=True)
class DatasetManifest:
    """Versioned dataset manifest recording provenance and lineage."""

    schema_version: str
    dataset_id: str
    content_hash: str
    source_ids: list[str]
    coverage: dict[str, list[str]]
    start_utc: datetime
    end_utc: datetime
    bar_count: int
    bar_schema_version: str
    created_at_utc: datetime
    updated_at_utc: datetime
    acquisition_code_version: str
    quality_report_ref: str
    parent_dataset_refs: list[str] = field(default_factory=list)
    excluded_period_refs: list[str] = field(default_factory=list)
    storage_uri: str = ""
    limitations: str = ""

    def __post_init__(self) -> None:
        self._validate_required()
        self._validate_times()
        self._validate_counts()
        self._validate_datetime_fields()
        self._validate_string_lists()

    def _validate_required(self) -> None:
        if not isinstance(self.schema_version, str) or not self.schema_version:
            raise InvalidDatasetManifestError("schema_version is required")
        if not isinstance(self.dataset_id, str) or not self.dataset_id:
            raise InvalidDatasetManifestError("dataset_id is required")
        if not isinstance(self.content_hash, str) or not self.content_hash:
            raise InvalidDatasetManifestError("content_hash is required")
        if not isinstance(self.storage_uri, str) or not self.storage_uri:
            raise InvalidDatasetManifestError("storage_uri is required")

    def _validate_times(self) -> None:
        if not isinstance(self.start_utc, datetime):
            raise InvalidDatasetManifestError("start_utc is required")
        if not isinstance(self.end_utc, datetime):
            raise InvalidDatasetManifestError("end_utc is required")
        if self.end_utc < self.start_utc:
            raise InvalidDatasetManifestError("end_utc must not be before start_utc")

    def _validate_counts(self) -> None:
        if not isinstance(self.bar_count, int) or self.bar_count < 0:
            raise InvalidDatasetManifestError("bar_count must be a non-negative int")

    def _validate_datetime_fields(self) -> None:
        for name in ("created_at_utc", "updated_at_utc"):
            value = getattr(self, name)
            if not isinstance(value, datetime):
                raise InvalidDatasetManifestError(f"{name} is required")

    def _validate_string_lists(self) -> None:
        if not isinstance(self.source_ids, list) or not all(
            isinstance(s, str) for s in self.source_ids
        ):
            raise InvalidDatasetManifestError("source_ids must be a list of strings")
        if not isinstance(self.coverage, dict) or not all(
            isinstance(k, str) and isinstance(v, list) and all(isinstance(x, str) for x in v)
            for k, v in self.coverage.items()
        ):
            raise InvalidDatasetManifestError(
                "coverage must be a dict of instrument -> list of timeframes"
            )
        if not isinstance(self.parent_dataset_refs, list) or not all(
            isinstance(s, str) for s in self.parent_dataset_refs
        ):
            raise InvalidDatasetManifestError("parent_dataset_refs must be a list of strings")
        if not isinstance(self.excluded_period_refs, list) or not all(
            isinstance(s, str) for s in self.excluded_period_refs
        ):
            raise InvalidDatasetManifestError("excluded_period_refs must be a list of strings")
