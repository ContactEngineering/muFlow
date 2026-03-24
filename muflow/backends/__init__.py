"""Execution backends for muflow."""

from muflow.backends.base import ExecutionBackend, LocalBackend

__all__ = ["ExecutionBackend", "LocalBackend"]

# LambdaBackend is optional (requires boto3)
try:
    from muflow.backends.lambda_backend import LambdaBackend, create_lambda_handler
    __all__.extend(["LambdaBackend", "create_lambda_handler"])
except ImportError:
    pass

# CeleryBackend and callbacks (Celery is optional)
try:
    from muflow.backends.celery_backend import CeleryBackend, create_celery_task
    from muflow.backends.callbacks import (
        CompletionCallback,
        CeleryCompletionCallback,
        NoOpCompletionCallback,
        LoggingCompletionCallback,
    )
    __all__.extend([
        "CeleryBackend",
        "create_celery_task",
        "CompletionCallback",
        "CeleryCompletionCallback",
        "NoOpCompletionCallback",
        "LoggingCompletionCallback",
    ])
except ImportError:
    pass
