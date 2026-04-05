"""Serializable handle for a submitted plan execution.

PlanHandle encapsulates the backend-specific plan ID and provides a
uniform interface for querying state and cancelling, without retaining
the backend instance.

This enables patterns like:

    # Django view submitting a plan:
    handle = backend.submit_plan(plan)
    record.plan_handle = handle.to_json()
    record.save()

    # Celery beat task polling status:
    for record in PendingRecord.objects.all():
        handle = PlanHandle.from_json(record.plan_handle)
        state = handle.get_state()
        if state in ("success", "failure"):
            record.state = state
            record.save()
"""

from __future__ import annotations

import logging
from typing import ClassVar, Literal, Optional

import pydantic

_log = logging.getLogger(__name__)

# Class-level Celery app reference, set by configure_celery()
_celery_app = None


class PlanHandle(pydantic.BaseModel):
    """Serializable reference to a submitted plan execution.

    Parameters
    ----------
    backend : str
        One of "local", "celery", "step_functions".
    plan_id : str
        Backend-specific plan identifier:
        - local: the plan's root_key
        - celery: Celery task/chord ID
        - step_functions: Step Functions execution ARN
    """

    model_config = pydantic.ConfigDict(extra="forbid")

    backend: Literal["local", "celery", "step_functions"]
    plan_id: str

    # Class-level Celery app — set once at startup via configure_celery()
    _celery_app: ClassVar[Optional[object]] = None

    @classmethod
    def configure_celery(cls, app) -> None:
        """Register the Celery app for use by get_state() / cancel().

        Call this once at application startup before any PlanHandle with
        backend="celery" is used outside of the CeleryBackend instance.

        Parameters
        ----------
        app
            Celery application instance.
        """
        cls._celery_app = app

    def get_state(self) -> str:
        """Return the current state of this plan execution.

        Returns
        -------
        str
            One of: "pending", "running", "success", "failure"
        """
        if self.backend == "local":
            # Local execution is always terminal by the time submit_plan()
            # returns a handle. Any failure raised an exception instead.
            return "success"

        if self.backend == "celery":
            return self._get_celery_state()

        if self.backend == "step_functions":
            return self._get_sfn_state()

        raise ValueError(f"Unknown backend: {self.backend!r}")

    def cancel(self) -> None:
        """Cancel the running plan.

        Raises
        ------
        NotImplementedError
            For LocalBackend (execution is always terminal).
        RuntimeError
            If Celery app is not configured.
        """
        if self.backend == "local":
            raise NotImplementedError(
                "LocalBackend executes synchronously and cannot be cancelled"
            )

        if self.backend == "celery":
            app = self.__class__._celery_app
            if app is None:
                raise RuntimeError(
                    "No Celery app configured. Call PlanHandle.configure_celery(app) first."
                )
            app.control.revoke(self.plan_id, terminate=True)
            _log.info(f"Cancelled Celery plan {self.plan_id}")
            return

        if self.backend == "step_functions":
            import boto3
            sfn = boto3.client("stepfunctions")
            sfn.stop_execution(
                executionArn=self.plan_id,
                cause="Cancelled by muflow PlanHandle",
            )
            _log.info(f"Stopped Step Functions execution: {self.plan_id}")
            return

        raise ValueError(f"Unknown backend: {self.backend!r}")

    def to_json(self) -> str:
        """Serialize this handle to a JSON string.

        The result can be stored (e.g., in a Django CharField) and later
        restored with :meth:`from_json`.
        """
        return self.model_dump_json()

    @classmethod
    def from_json(cls, s: str) -> "PlanHandle":
        """Restore a handle from a JSON string produced by :meth:`to_json`.

        Parameters
        ----------
        s : str
            JSON string.
        """
        return cls.model_validate_json(s)

    # ── Private helpers ───────────────────────────────────────────────────

    def _get_celery_state(self) -> str:
        app = self.__class__._celery_app
        if app is None:
            raise RuntimeError(
                "No Celery app configured. Call PlanHandle.configure_celery(app) first."
            )
        from celery.result import AsyncResult
        result = AsyncResult(self.plan_id, app=app)

        state_map = {
            "PENDING": "pending",
            "STARTED": "running",
            "SUCCESS": "success",
            "FAILURE": "failure",
            "REVOKED": "failure",
        }

        if not hasattr(result, "state"):
            # GroupResult
            if result.ready():
                return "failure" if result.failed() else "success"
            return "running"

        return state_map.get(result.state, "pending")

    def _get_sfn_state(self) -> str:
        import boto3
        sfn = boto3.client("stepfunctions")
        resp = sfn.describe_execution(executionArn=self.plan_id)
        return {
            "RUNNING": "running",
            "SUCCEEDED": "success",
            "FAILED": "failure",
            "TIMED_OUT": "failure",
            "ABORTED": "failure",
        }.get(resp["status"], "pending")
