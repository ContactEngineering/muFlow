"""Workflow context abstractions.

This package provides the ``WorkflowContext`` class that wraps a
``StorageBackend`` (from ``muflow.storage``) and adds workflow-level
concerns: dependency access and progress reporting.

The unified ``WorkflowContext`` class works with any storage backend,
eliminating the need for separate context classes per backend type.

Modules
-------
workflow
    ``WorkflowContext`` — unified context class for all backends.
base
    ``WorkflowContextProtocol`` — protocol for type checking.
parameterized
    ``ParameterizedMixin`` — adds ``kwargs`` and ``parameters`` support.
local
    ``LocalFolderContext`` — deprecated, use WorkflowContext instead.
s3
    ``S3WorkflowContext`` — deprecated, use WorkflowContext instead.
"""

from muflow.context.base import WorkflowContext as WorkflowContextProtocol
from muflow.context.local import LocalFolderContext
from muflow.context.parameterized import ParameterizedMixin
from muflow.context.s3 import S3WorkflowContext
from muflow.context.workflow import WorkflowContext, create_local_context

__all__ = [
    "WorkflowContext",
    "WorkflowContextProtocol",
    "ParameterizedMixin",
    "create_local_context",
    # Deprecated - kept for backward compatibility
    "LocalFolderContext",
    "S3WorkflowContext",
]
