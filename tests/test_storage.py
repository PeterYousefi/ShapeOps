import stat
import pytest

from backend.storage import (
    AzureBlobStorageAdapter,
    LocalStorageAdapter,
    MAX_OBJECT_BYTES,
    get_storage_adapter,
    sanitize_key,
)


def test_sanitize_key():
    assert sanitize_key("manifest.json") == "manifest.json"
    assert sanitize_key("models/manifest.json") == "models/manifest.json"
    assert sanitize_key("foo/bar/baz.bin") == "foo/bar/baz.bin"

    with pytest.raises(ValueError, match="non-empty"):
        sanitize_key("")
    with pytest.raises(ValueError, match="non-empty"):
        sanitize_key(None)  # type: ignore

    with pytest.raises(ValueError, match="null bytes"):
        sanitize_key("foo\x00bar")

    # Path traversal
    with pytest.raises(ValueError, match="Path traversal"):
        sanitize_key("../secret")
    with pytest.raises(ValueError, match="Path traversal"):
        sanitize_key("/absolute/path")
    with pytest.raises(ValueError, match="Path traversal"):
        sanitize_key("foo/../../bar")
    with pytest.raises(ValueError, match="root directory"):
        sanitize_key(".")


def test_local_storage_adapter_roundtrip(tmp_path):
    adapter = LocalStorageAdapter(root=tmp_path)

    # Basic put and get
    key = "artifacts/report.json"
    data = b'{"status": "ok"}'
    adapter.put_bytes(key, data, content_type="application/json")

    assert adapter.exists(key) is True
    assert adapter.get_bytes(key) == data

    # Verify atomic file mode is 0600
    target = tmp_path / "artifacts" / "report.json"
    assert target.exists()
    mode = target.stat().st_mode & 0o777
    assert mode == (stat.S_IRUSR | stat.S_IWUSR)

    # List keys
    assert adapter.list_keys("artifacts") == ["artifacts/report.json"]
    assert adapter.list_keys("other") == []

    # Max bytes enforcement on read
    with pytest.raises(ValueError, match="max_bytes"):
        adapter.get_bytes(key, max_bytes=5)

    # Delete
    assert adapter.delete(key) is True
    assert adapter.exists(key) is False
    assert adapter.delete(key) is False

    with pytest.raises(FileNotFoundError):
        adapter.get_bytes(key)


def test_local_storage_adapter_limits_and_traversal(tmp_path):
    adapter = LocalStorageAdapter(root=tmp_path)

    # Oversized payload
    with pytest.raises(ValueError, match="Payload size"):
        adapter.put_bytes("large.bin", b"x" * (MAX_OBJECT_BYTES + 1))

    # Path traversal attempt
    with pytest.raises(ValueError, match="Path traversal"):
        adapter.put_bytes("../escape.bin", b"data")


def test_azure_blob_storage_adapter_validation():
    with pytest.raises(ValueError, match="https URL"):
        AzureBlobStorageAdapter(account_url="http://insecure.url", container_name="artifacts")
    with pytest.raises(ValueError, match="https URL"):
        AzureBlobStorageAdapter(account_url="", container_name="artifacts")
    with pytest.raises(ValueError, match="valid Azure Blob container name"):
        AzureBlobStorageAdapter(
            account_url="https://shapeops.blob.core.windows.net", container_name="ab"
        )


class MockBlobClient:
    def __init__(self, data: bytes = b""):
        self.data = data
        self.uploaded_content_type = None

    def upload_blob(self, data, overwrite=True, content_type=None):
        self.data = data
        self.uploaded_content_type = content_type

    def download_blob(self, max_concurrency=1):
        class Stream:
            def __init__(self, d):
                self.d = d

            def readall(self):
                return self.d

        return Stream(self.data)

    def exists(self):
        return len(self.data) > 0

    def delete_blob(self):
        self.data = b""


class MockContainerClient:
    def __init__(self):
        self.blobs = {}

    def get_blob_client(self, name):
        if name not in self.blobs:
            self.blobs[name] = MockBlobClient()
        return self.blobs[name]

    def list_blobs(self, name_starts_with=""):
        return [{"name": k} for k in sorted(self.blobs) if k.startswith(name_starts_with)]


def test_azure_blob_storage_adapter_mock_client():
    mock_container = MockContainerClient()
    adapter = AzureBlobStorageAdapter(
        account_url="https://shapeops.blob.core.windows.net",
        container_name="shapeops-artifacts",
        client=mock_container,
    )

    key = "models/model.pkl"
    payload = b"dummy_model_bytes"
    adapter.put_bytes(key, payload, content_type="application/octet-stream")

    assert adapter.exists(key) is True
    assert adapter.get_bytes(key) == payload
    assert adapter.list_keys("models") == ["models/model.pkl"]
    assert adapter.delete(key) is True


def test_get_storage_adapter_factory(tmp_path, monkeypatch):
    monkeypatch.setenv("SHAPEOPS_STORAGE_TYPE", "local")
    monkeypatch.setenv("SHAPEOPS_DATA_DIR", str(tmp_path))

    adapter = get_storage_adapter()
    assert isinstance(adapter, LocalStorageAdapter)

    monkeypatch.setenv("SHAPEOPS_STORAGE_TYPE", "azure")
    monkeypatch.setenv("SHAPEOPS_AZURE_STORAGE_URL", "https://shapeops.blob.core.windows.net")
    monkeypatch.setenv("SHAPEOPS_AZURE_CONTAINER", "my-container")

    azure_adapter = get_storage_adapter()
    assert isinstance(azure_adapter, AzureBlobStorageAdapter)
    assert azure_adapter.account_url == "https://shapeops.blob.core.windows.net"
    assert azure_adapter.container_name == "my-container"
