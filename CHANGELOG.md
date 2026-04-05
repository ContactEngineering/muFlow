# Changelog

## v0.2.0 (not yet released)

### Breaking changes

- Renamed "workflow" to "task" across the entire codebase (`Workflow` -> `Task`, `@register_workflow` -> `@register_task`, etc.).
- Removed `TaskContextProtocol`. Use `TaskContext` directly instead.
- **Caching moved to execution time**: `Pipeline.build_plan()` no longer accepts an `is_cached` callback. Cache detection now happens automatically inside `execute_task()` — if `manifest.json` already exists at the task's storage prefix, the task is skipped without re-running. Remove any `is_cached=...` arguments from `build_plan()` calls and any `LocalStorageBackend.make_cache_checker()` / `is_result_cached()` usage.
- `TaskNode.cached` field removed. Tasks are no longer pre-marked cached at plan-build time.
- `run_plan_locally()` no longer accepts a `use_cache` parameter. Caching is always active and requires no configuration.
- `LocalStorageBackend.make_cache_checker()` and `LocalStorageBackend.is_result_cached()` removed.
- `ExecutionResult` gains a new `cached: bool` field (default `False`) indicating whether the task was skipped due to an existing result.

## v0.1.0 (2026-04-04)

Initial release.

### Features

- **Task registry**: `@register_task` decorator for registering pure
  task functions with optional Pydantic parameter validation
- **Pipeline abstraction**: `Pipeline`, `Step`, and `ForEach` for declarative
  multi-step DAG definitions
- **TaskPlan**: Static, serializable DAG representation compiled from
  pipelines via topological sort
- **Content-addressed storage**: Deterministic prefix computation with
  `IdentityKey` annotations for cache control
- **TaskContext**: Unified file I/O interface (JSON, xarray, raw bytes)
  with dependency access and progress reporting

### Execution backends

- **LocalBackend**: Synchronous in-process execution for testing and CLI use
- **CeleryBackend**: Parallel DAG execution via Celery chord/group primitives
- **StepFunctionsBackend**: AWS Step Functions orchestration with Lambda

### Storage backends

- **LocalStorageBackend**: Filesystem-based storage with write-once semantics
  and path traversal protection
- **S3StorageBackend**: AWS S3 storage backend

### Utilities

- `run_plan_locally()` helper for pipeline integration testing
- `ResourceManager` and `resolve_uri` for transparent local/remote resource
  fetching
- Extended JSON encoder with NaN, numpy, and datetime support
- xarray Dataset serialization helpers
