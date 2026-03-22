"""Tests for WorkflowContext implementations."""

import tempfile
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from muflows import LocalFolderContext, WorkflowContext


class TestLocalFolderContext:
    """Tests for LocalFolderContext."""

    def test_implements_protocol(self):
        """LocalFolderContext should implement WorkflowContext protocol."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = LocalFolderContext(path=tmpdir, kwargs={})
            assert isinstance(ctx, WorkflowContext)

    def test_storage_prefix(self):
        """storage_prefix should return the path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = LocalFolderContext(path=tmpdir, kwargs={})
            assert ctx.storage_prefix == tmpdir

    def test_kwargs(self):
        """kwargs should return the provided parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            kwargs = {"param1": "value1", "param2": 42}
            ctx = LocalFolderContext(path=tmpdir, kwargs=kwargs)
            assert ctx.kwargs == kwargs

    def test_save_and_read_json(self):
        """Should save and read JSON files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = LocalFolderContext(path=tmpdir, kwargs={})

            data = {"key": "value", "number": 42, "nested": {"a": 1}}
            ctx.save_json("test.json", data)

            assert ctx.exists("test.json")
            loaded = ctx.read_json("test.json")
            assert loaded == data

    def test_save_and_read_json_with_nan(self):
        """Should handle NaN values in JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = LocalFolderContext(path=tmpdir, kwargs={})

            data = {"value": float("nan"), "inf": float("inf")}
            ctx.save_json("test.json", data)

            loaded = ctx.read_json("test.json")
            assert np.isnan(loaded["value"])
            assert np.isinf(loaded["inf"])

    def test_save_and_read_file(self):
        """Should save and read raw bytes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = LocalFolderContext(path=tmpdir, kwargs={})

            data = b"Hello, World!"
            ctx.save_file("test.txt", data)

            assert ctx.exists("test.txt")
            loaded = ctx.read_file("test.txt")
            assert loaded == data

    def test_save_and_read_xarray(self):
        """Should save and read xarray Datasets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = LocalFolderContext(path=tmpdir, kwargs={})

            ds = xr.Dataset({
                "temperature": (["x", "y"], np.random.rand(3, 4)),
                "pressure": (["x", "y"], np.random.rand(3, 4)),
            })
            ctx.save_xarray("test.nc", ds)

            assert ctx.exists("test.nc")
            loaded = ctx.read_xarray("test.nc")
            assert "temperature" in loaded
            assert "pressure" in loaded
            np.testing.assert_array_almost_equal(
                loaded["temperature"].values,
                ds["temperature"].values,
            )

    def test_open_file(self):
        """Should open files for reading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = LocalFolderContext(path=tmpdir, kwargs={})

            ctx.save_json("test.json", {"key": "value"})

            with ctx.open_file("test.json", "r") as f:
                content = f.read()
                assert "key" in content
                assert "value" in content

    def test_exists_false_for_missing(self):
        """exists() should return False for missing files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = LocalFolderContext(path=tmpdir, kwargs={})
            assert not ctx.exists("nonexistent.json")

    def test_nested_directories(self):
        """Should handle nested directory paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = LocalFolderContext(path=tmpdir, kwargs={})

            ctx.save_json("subdir/nested/test.json", {"key": "value"})
            assert ctx.exists("subdir/nested/test.json")
            loaded = ctx.read_json("subdir/nested/test.json")
            assert loaded == {"key": "value"}

    def test_dependency_access(self):
        """Should access dependency outputs via dependency()."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create dependency output
            dep_path = Path(tmpdir) / "dependency"
            dep_path.mkdir()
            dep_ctx = LocalFolderContext(path=str(dep_path), kwargs={})
            dep_ctx.save_json("result.json", {"dep_value": 123})

            # Create main context with dependency
            main_path = Path(tmpdir) / "main"
            main_ctx = LocalFolderContext(
                path=str(main_path),
                kwargs={},
                dependency_paths={"dep1": str(dep_path)},
            )

            # Access dependency
            dep = main_ctx.dependency("dep1")
            result = dep.read_json("result.json")
            assert result == {"dep_value": 123}

    def test_dependency_unknown_raises(self):
        """dependency() should raise KeyError for unknown dependencies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = LocalFolderContext(path=tmpdir, kwargs={})

            with pytest.raises(KeyError):
                ctx.dependency("unknown")

    def test_creates_directory_if_missing(self):
        """Should create the directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "new_dir"
            assert not path.exists()

            ctx = LocalFolderContext(path=str(path), kwargs={})
            assert path.exists()
