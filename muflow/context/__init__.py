"""Workflow context abstractions.

This package provides the ``WorkflowContext`` protocol and its
implementations.  Each context wraps a ``StorageBackend`` (from
``muflow.storage``) and adds workflow-level concerns: validated parameters,
dependency access, and progress reporting.

The protocol is domain-agnostic.  Domain-specific contexts (e.g.
``TopographyContext``, ``SurfaceContext``) live downstream in sds-workflows.

Modules
-------
base
    ``WorkflowContext`` protocol — the abstract interface that all contexts
    implement.
local
    ``LocalFolderContext`` — backed by a ``LocalStorageBackend``.
s3
    ``S3WorkflowContext`` — backed by an ``S3StorageBackend``.
"""

from muflow.context.base import WorkflowContext
from muflow.context.local import LocalFolderContext
from muflow.context.s3 import S3WorkflowContext

__all__ = [
    "WorkflowContext",
    "LocalFolderContext",
    "S3WorkflowContext",
]
