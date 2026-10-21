"""Storage module supporting local filesystem and Azure Blob Storage adapters."""
import os
from pathlib import Path
import stat
import tempfile
from typing import Protocol, runtime_checkable

MAX_OBJECT_BYTES = 16 * 1024 * 1024  # 16 MiB max object size


def sanitize_key(key: str) -> str:
    """Validate and normalize an object key, preventing path traversal."""
    if not key or not isinstance(key, str):
        raise ValueError("Storage key must be a non-empty string")
    if "\x00" in key:
        raise ValueError("Storage key must not contain null bytes")
    normalized = os.path.normpath(key)
    if normalized.startswith("/") or normalized.startswith("\\") or normalized.startswith("..") or "/../" in normalized:
        raise ValueError(f"Path traversal detected in storage key: {key}")
    if normalized == ".":
        raise ValueError("Storage key must not be root directory")
    return normalized.replace("\\", "/")


@runtime_checkable
class StorageAdapter(Protocol):
    def put_bytes(self, key: str, data: bytes, *, content_type: str | None = None) -> None:
        """Store bytes at key atomically."""
        ...

    def get_bytes(self, key: str, *, max_bytes: int = MAX_OBJECT_BYTES) -> bytes:
        """Retrieve bytes at key bounded by max_bytes."""
        ...

    def exists(self, key: str) -> bool:
        """Check whether key exists."""
        ...

    def list_keys(self, prefix: str = "", *, limit: int = 1000) -> list[str]:
        """List keys matching prefix up to limit."""
        ...

    def delete(self, key: str) -> bool:
        """Delete object at key, returning True if deleted."""
        ...


class LocalStorageAdapter:
    """Local filesystem storage adapter with atomic writes, private permissions, and traversal defense."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        clean = sanitize_key(key)
        target = (self.root / clean).resolve()
        # Enforce that target is strictly within self.root
        if not str(target).startswith(str(self.root) + os.sep) and target != self.root:
            raise ValueError(f"Resolved path escapes storage root: {key}")
        return target

    def put_bytes(self, key: str, data: bytes, *, content_type: str | None = None) -> None:
        if not isinstance(data, (bytes, bytearray)):
            raise ValueError("Data must be bytes")
        if len(data) > MAX_OBJECT_BYTES:
            raise ValueError(f"Payload size {len(data)} exceeds limit of {MAX_OBJECT_BYTES} bytes")
        target = self._resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
            staging = Path(stream.name)
            try:
                os.chmod(staging, stat.S_IRUSR | stat.S_IWUSR)
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            except BaseException:
                staging.unlink(missing_ok=True)
                raise

        staging.replace(target)

    def get_bytes(self, key: str, *, max_bytes: int = MAX_OBJECT_BYTES) -> bytes:
        target = self._resolve(key)
        if not target.exists():
            raise FileNotFoundError(f"Object not found: {key}")
        if not stat.S_ISREG(target.lstat().st_mode):
            raise ValueError(f"Object is not a regular file: {key}")
        size = target.stat().st_size
        if size > max_bytes:
            raise ValueError(f"Object size {size} exceeds max_bytes limit {max_bytes}")
        with target.open("rb") as stream:
            content = stream.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise ValueError(f"Object content exceeds max_bytes limit {max_bytes}")
        return content

    def exists(self, key: str) -> bool:
        try:
            target = self._resolve(key)
            return target.exists() and stat.S_ISREG(target.lstat().st_mode)
        except (ValueError, OSError):
            return False

    def list_keys(self, prefix: str = "", *, limit: int = 1000) -> list[str]:
        if not 1 <= limit <= 10000:
            raise ValueError("Limit must be between 1 and 10000")
        clean_prefix = sanitize_key(prefix) if prefix else ""
        results = []
        for path in sorted(self.root.rglob("*")):
            if stat.S_ISREG(path.lstat().st_mode):
                rel = path.relative_to(self.root).as_posix()
                if not clean_prefix or rel.startswith(clean_prefix):
                    results.append(rel)
                    if len(results) >= limit:
                        break
        return results

    def delete(self, key: str) -> bool:
        target = self._resolve(key)
        if target.exists() and stat.S_ISREG(target.lstat().st_mode):
            target.unlink()
            return True
        return False


class AzureBlobStorageAdapter:
    """Production-ready Azure Blob Storage adapter using Managed Identity (DefaultAzureCredential)."""

    def __init__(
        self,
        account_url: str,
        container_name: str,
        *,
        credential: object = None,
        client: object = None,
    ) -> None:
        if not account_url or not isinstance(account_url, str) or not account_url.startswith("https://"):
            raise ValueError("account_url must be a valid https URL (e.g. https://<account>.blob.core.windows.net)")
        if not container_name or not isinstance(container_name, str) or len(container_name) < 3:
            raise ValueError("container_name must be a valid Azure Blob container name")

        self.account_url = account_url
        self.container_name = container_name
        self._client = client
        self._credential = credential

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from azure.storage.blob import ContainerClient  # type: ignore
            from azure.identity import DefaultAzureCredential  # type: ignore
        except ImportError:
            raise RuntimeError(
                "azure-storage-blob and azure-identity packages are required for AzureBlobStorageAdapter. "
                "Use LocalStorageAdapter for local development without Azure dependencies."
            ) from None

        cred = self._credential if self._credential is not None else DefaultAzureCredential()
        self._client = ContainerClient(
            account_url=self.account_url,
            container_name=self.container_name,
            credential=cred,
        )
        return self._client

    def put_bytes(self, key: str, data: bytes, *, content_type: str | None = None) -> None:
        clean = sanitize_key(key)
        if len(data) > MAX_OBJECT_BYTES:
            raise ValueError(f"Payload size {len(data)} exceeds limit of {MAX_OBJECT_BYTES} bytes")
        client = self._get_client()
        blob = client.get_blob_client(clean)
        blob.upload_blob(data, overwrite=True, content_type=content_type)

    def get_bytes(self, key: str, *, max_bytes: int = MAX_OBJECT_BYTES) -> bytes:
        clean = sanitize_key(key)
        client = self._get_client()
        blob = client.get_blob_client(clean)
        stream = blob.download_blob(max_concurrency=1)
        data = stream.readall()
        if len(data) > max_bytes:
            raise ValueError(f"Downloaded blob exceeds max_bytes limit {max_bytes}")
        return data

    def exists(self, key: str) -> bool:
        clean = sanitize_key(key)
        client = self._get_client()
        blob = client.get_blob_client(clean)
        return bool(blob.exists())

    def list_keys(self, prefix: str = "", *, limit: int = 1000) -> list[str]:
        clean_prefix = sanitize_key(prefix) if prefix else ""
        client = self._get_client()
        results = []
        for item in client.list_blobs(name_starts_with=clean_prefix):
            name = item.name if hasattr(item, "name") else item["name"]
            results.append(name)
            if len(results) >= limit:
                break
        return results

    def delete(self, key: str) -> bool:
        clean = sanitize_key(key)
        client = self._get_client()
        blob = client.get_blob_client(clean)
        if blob.exists():
            blob.delete_blob()
            return True
        return False


def get_storage_adapter() -> StorageAdapter:
    """Factory creating configured storage adapter based on environment."""
    storage_type = os.getenv("SHAPEOPS_STORAGE_TYPE", "local").lower()
    if storage_type == "azure":
        account_url = os.getenv("SHAPEOPS_AZURE_STORAGE_URL", "")
        container = os.getenv("SHAPEOPS_AZURE_CONTAINER", "shapeops-artifacts")
        return AzureBlobStorageAdapter(account_url=account_url, container_name=container)

    data_dir = os.getenv("SHAPEOPS_DATA_DIR", ".runtime")
    storage_root = Path(data_dir) / "storage"
    return LocalStorageAdapter(root=storage_root)
