"""S3 workflow context."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import IO, Any

import xarray as xr

from muflow.io.json import dumps_json
from muflow.storage import S3StorageBackend


class S3WorkflowContext:
    """WorkflowContext backed by S3.

    Delegates all file I/O to an ``S3StorageBackend``.  The storage backend
    provides path traversal protection, write-once semantics, protected file
    enforcement, and manifest generation.

    Parameters
    ----------
    storage_prefix : str
        S3 key prefix for this workflow's output files.
    kwargs : dict
        Workflow parameters.
    dependency_prefixes : dict[str, str]
        Mapping from dependency key to S3 prefix.
    bucket : str
        S3 bucket name.
    s3_client : optional
        Boto3 S3 client.  If not provided, one will be created.
    storage : S3StorageBackend, optional
        Pre-created storage backend.  If not provided, one is created from
        *storage_prefix*, *bucket*, and *s3_client*.
    """

    def __init__(
        self,
        storage_prefix: str,
        kwargs: dict,
        dependency_prefixes: dict[str, str],
        bucket: str,
        s3_client=None,
        storage: S3StorageBackend = None,
    ):
        self._storage = storage or S3StorageBackend(
            storage_prefix, bucket, s3_client
        )
        self._kwargs = kwargs
        self._dep_prefixes = dependency_prefixes
        self._bucket = bucket
        # Keep s3_client reference for dependency and progress contexts
        self._s3 = self._storage._s3
        self._parameters = None  # Set by executor for function-based workflows

    @property
    def storage(self) -> S3StorageBackend:
        """Return the underlying storage backend."""
        return self._storage

    @property
    def storage_prefix(self) -> str:
        """Return the S3 key prefix."""
        return self._storage.storage_prefix

    @property
    def kwargs(self) -> dict:
        """Return workflow parameters."""
        return self._kwargs

    @property
    def parameters(self):
        """Return validated parameters (pydantic model), or None."""
        return self._parameters

    # ── File I/O (delegated to storage backend) ─────────────────────────

    def save_file(self, filename: str, data: bytes) -> None:
        """Save raw bytes to S3."""
        self._storage.save_file(filename, data)

    def save_json(self, filename: str, data: Any) -> None:
        """Save data as JSON to S3."""
        self._storage.save_json(filename, data)

    def save_xarray(self, filename: str, dataset: xr.Dataset) -> None:
        """Save an xarray Dataset as NetCDF to S3."""
        self._storage.save_xarray(filename, dataset)

    def open_file(self, filename: str, mode: str = "r") -> IO:
        """Open a file from S3 for reading."""
        return self._storage.open_file(filename, mode)

    def read_file(self, filename: str) -> bytes:
        """Read raw bytes from S3."""
        return self._storage.read_file(filename)

    def read_json(self, filename: str) -> Any:
        """Read and parse a JSON file from S3."""
        return self._storage.read_json(filename)

    def read_xarray(self, filename: str) -> xr.Dataset:
        """Read a NetCDF file from S3 as xarray Dataset."""
        return self._storage.read_xarray(filename)

    def exists(self, filename: str) -> bool:
        """Check if a file exists in S3."""
        return self._storage.exists(filename)

    # ── Dependency access ───────────────────────────────────────────────

    def dependency(self, key: str) -> S3WorkflowContext:
        """Get a read-only context for accessing a dependency's outputs."""
        if key not in self._dep_prefixes:
            raise KeyError(f"Unknown dependency: {key}")
        return S3WorkflowContext(
            storage_prefix=self._dep_prefixes[key],
            kwargs={},
            dependency_prefixes={},
            bucket=self._bucket,
            s3_client=self._s3,
        )

    # ── Progress reporting ──────────────────────────────────────────────

    def report_progress(self, current: int, total: int, message: str = "") -> None:
        """Report progress by writing ``_progress.json`` to S3."""
        progress_data = {
            "current": current,
            "total": total,
            "message": message,
            "percentage": (current / total * 100) if total > 0 else 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        body = dumps_json(progress_data).encode("utf-8")
        # Write directly via boto3 — _progress.json is an internal file,
        # not subject to write-once or protected-file rules.
        self._s3.put_object(
            Bucket=self._bucket,
            Key=f"{self.storage_prefix}/_progress.json",
            Body=body,
            ContentType="application/json",
        )
