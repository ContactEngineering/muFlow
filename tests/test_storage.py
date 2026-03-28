"""Tests for storage backends."""

import json

import numpy as np
import pytest
import xarray as xr

from muflow.storage import LocalStorageBackend, StorageBackend
from muflow.storage.base import PROTECTED_FILES, validate_filename, validate_writable


# ── validate_filename tests ─────────────────────────────────────────────────


class TestValidateFilename:
    def test_valid_simple(self):
        validate_filename("result.json")

    def test_valid_nested(self):
        validate_filename("subdir/result.json")

    def test_empty(self):
        with pytest.raises(ValueError, match="empty"):
            validate_filename("")

    def test_absolute_path(self):
        with pytest.raises(ValueError, match="Absolute"):
            validate_filename("/etc/passwd")

    def test_dotdot_prefix(self):
        with pytest.raises(ValueError, match="traversal"):
            validate_filename("../escape")

    def test_dotdot_middle(self):
        with pytest.raises(ValueError, match="traversal"):
            validate_filename("foo/../../bar")

    def test_dotdot_normalised(self):
        # "./foo/../bar" normalises to "bar" which is safe
        validate_filename("./foo/../foo/bar")

    def test_dotdot_only(self):
        with pytest.raises(ValueError, match="traversal"):
            validate_filename("..")


# ── validate_writable tests ─────────────────────────────────────────────────


class TestValidateWritable:
    def test_protected_context_json(self):
        with pytest.raises(PermissionError, match="protected"):
            validate_writable("context.json", set())

    def test_protected_manifest_json(self):
        with pytest.raises(PermissionError, match="protected"):
            validate_writable("manifest.json", set())

    def test_already_written(self):
        with pytest.raises(FileExistsError, match="already been written"):
            validate_writable("data.json", {"data.json"})

    def test_normal_write(self):
        validate_writable("data.json", set())


# ── LocalStorageBackend tests ───────────────────────────────────────────────


class TestLocalStorageBackend:
    def test_implements_protocol(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        assert isinstance(backend, StorageBackend)

    def test_storage_prefix(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        assert backend.storage_prefix == str(tmp_path)

    def test_creates_directory(self, tmp_path):
        new_dir = tmp_path / "new" / "nested"
        backend = LocalStorageBackend(new_dir)
        assert new_dir.exists()

    # ── JSON round-trip ─────────────────────────────────────────────────

    def test_save_read_json(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        backend.save_json("data.json", {"key": "value", "n": 42})
        result = backend.read_json("data.json")
        assert result == {"key": "value", "n": 42}

    def test_save_read_json_with_nan(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        backend.save_json("data.json", {"x": float("nan")})
        result = backend.read_json("data.json")
        assert np.isnan(result["x"])

    # ── Bytes round-trip ────────────────────────────────────────────────

    def test_save_read_file(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        backend.save_file("data.bin", b"\x00\x01\x02")
        assert backend.read_file("data.bin") == b"\x00\x01\x02"

    # ── xarray round-trip ───────────────────────────────────────────────

    def test_save_read_xarray(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        ds = xr.Dataset({"temp": (["x"], [1.0, 2.0, 3.0])})
        backend.save_xarray("model.nc", ds)
        result = backend.read_xarray("model.nc")
        xr.testing.assert_equal(ds, result)

    # ── open_file ───────────────────────────────────────────────────────

    def test_open_file(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        backend.save_file("text.txt", b"hello")
        with backend.open_file("text.txt", "r") as f:
            assert f.read() == "hello"

    # ── exists ──────────────────────────────────────────────────────────

    def test_exists(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        assert not backend.exists("nope.json")
        backend.save_json("data.json", {})
        assert backend.exists("data.json")

    # ── Nested directories ──────────────────────────────────────────────

    def test_nested_save(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        backend.save_json("sub/dir/data.json", {"nested": True})
        assert backend.read_json("sub/dir/data.json") == {"nested": True}

    # ── written_files tracking ──────────────────────────────────────────

    def test_written_files_empty(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        assert backend.written_files == frozenset()

    def test_written_files_tracked(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        backend.save_json("a.json", {})
        backend.save_file("b.bin", b"")
        assert backend.written_files == frozenset({"a.json", "b.bin"})

    # ── Write-once enforcement ──────────────────────────────────────────

    def test_write_once_json(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        backend.save_json("data.json", {"v": 1})
        with pytest.raises(FileExistsError):
            backend.save_json("data.json", {"v": 2})

    def test_write_once_file(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        backend.save_file("data.bin", b"first")
        with pytest.raises(FileExistsError):
            backend.save_file("data.bin", b"second")

    def test_write_once_xarray(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        ds = xr.Dataset({"x": (["i"], [1.0])})
        backend.save_xarray("model.nc", ds)
        with pytest.raises(FileExistsError):
            backend.save_xarray("model.nc", ds)

    # ── Protected files ─────────────────────────────────────────────────

    def test_cannot_write_context_json(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        with pytest.raises(PermissionError, match="protected"):
            backend.save_json("context.json", {})

    def test_cannot_write_manifest_json(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        with pytest.raises(PermissionError, match="protected"):
            backend.save_json("manifest.json", {})

    def test_can_read_context_json(self, tmp_path):
        """context.json is written by orchestration, but readable."""
        (tmp_path / "context.json").write_text('{"type": "test"}')
        backend = LocalStorageBackend(tmp_path)
        assert backend.read_json("context.json") == {"type": "test"}

    # ── Path traversal protection ───────────────────────────────────────

    def test_save_rejects_dotdot(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        with pytest.raises(ValueError, match="traversal"):
            backend.save_json("../escape.json", {})

    def test_save_rejects_absolute(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        with pytest.raises(ValueError, match="Absolute"):
            backend.save_json("/tmp/escape.json", {})

    def test_read_rejects_dotdot(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        with pytest.raises(ValueError, match="traversal"):
            backend.read_json("../escape.json")

    # ── Manifest ────────────────────────────────────────────────────────

    def test_write_manifest(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        backend.save_json("a.json", {})
        backend.save_file("b.bin", b"")
        backend.write_manifest()

        manifest = json.loads((tmp_path / "manifest.json").read_text())
        assert manifest["files"] == ["a.json", "b.bin"]
        assert "timestamp" in manifest

    def test_write_manifest_empty(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        backend.write_manifest()
        manifest = json.loads((tmp_path / "manifest.json").read_text())
        assert manifest["files"] == []
