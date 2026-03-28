"""Workflow context protocol.

The WorkflowContext protocol defines the interface that workflow functions
receive.  It provides file I/O (delegated to a storage backend), dependency
access, progress reporting, and validated parameters.

The protocol is deliberately domain-agnostic.  Domain-specific contexts
(e.g. TopographyContext, SurfaceContext) are defined downstream in
sds-workflows, not here.
"""

from __future__ import annotations

from typing import IO, Any, Protocol, runtime_checkable

import xarray as xr

from muflow.storage.base import StorageBackend


@runtime_checkable
class WorkflowContext(Protocol):
    """Abstract interface for workflow execution contexts.

    A context wraps a ``StorageBackend`` and adds workflow-level concerns:
    validated parameters, dependency access, and progress reporting.
    Implementations delegate file I/O to the storage backend, which enforces
    path traversal protection, write-once semantics, and protected files.
    """

    @property
    def storage(self) -> StorageBackend:
        """The underlying storage backend."""
        ...

    @property
    def storage_prefix(self) -> str:
        """Root path or S3 prefix for this workflow's output files."""
        ...

    @property
    def kwargs(self) -> dict:
        """Raw parameters dict passed to this workflow."""
        ...

    @property
    def parameters(self) -> Any:
        """Validated parameters (pydantic model), or None.

        Set by the executor after parameter validation.  Workflow functions
        should prefer ``context.parameters.my_param`` over ``context.kwargs``.
        """
        ...

    # ── File I/O (delegated to storage backend) ─────────────────────────

    def save_file(self, filename: str, data: bytes) -> None:
        """Save raw bytes to a file."""
        ...

    def save_json(self, filename: str, data: Any) -> None:
        """Save data as JSON."""
        ...

    def save_xarray(self, filename: str, dataset: xr.Dataset) -> None:
        """Save an xarray Dataset as NetCDF."""
        ...

    def open_file(self, filename: str, mode: str = "r") -> IO:
        """Open a file for reading."""
        ...

    def read_file(self, filename: str) -> bytes:
        """Read raw bytes from a file."""
        ...

    def read_json(self, filename: str) -> Any:
        """Read and parse a JSON file."""
        ...

    def read_xarray(self, filename: str) -> xr.Dataset:
        """Read a NetCDF file as xarray Dataset."""
        ...

    def exists(self, filename: str) -> bool:
        """Check if a file exists."""
        ...

    # ── Dependency access ───────────────────────────────────────────────

    def dependency(self, key: str) -> WorkflowContext:
        """Get a context for accessing a completed dependency's outputs."""
        ...

    # ── Progress reporting ──────────────────────────────────────────────

    def report_progress(self, current: int, total: int, message: str = "") -> None:
        """Report progress (may be no-op on serverless backends)."""
        ...
