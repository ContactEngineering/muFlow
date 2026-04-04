"""Workflow context.

This package provides the ``WorkflowContext`` class that wraps a
``StorageBackend`` (from ``muflow.storage``) and adds workflow-level
concerns: dependency access, progress reporting, and parameters.

Modules
-------
workflow
    ``WorkflowContext`` — unified context class for all backends.
    ``create_local_context`` — convenience function for local testing.
"""

from muflow.context.workflow import WorkflowContext, create_local_context

__all__ = [
    "WorkflowContext",
    "create_local_context",
]
