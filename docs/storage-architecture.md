# Storage Architecture & Cloud Adapters

ShapeOps implements a unified, typed storage abstraction to support both local-first offline development and Azure cloud production deployment without hardcoded secrets or environment-specific forks.

## Storage Abstraction Contract

The storage layer is defined by the `StorageAdapter` protocol in `backend/storage.py`:

```python
class StorageAdapter(Protocol):
    def put_bytes(self, key: str, data: bytes, *, content_type: str | None = None) -> None: ...
    def get_bytes(self, key: str, *, max_bytes: int = MAX_OBJECT_BYTES) -> bytes: ...
    def exists(self, key: str) -> bool: ...
    def list_keys(self, prefix: str = "", *, limit: int = 1000) -> list[str]: ...
    def delete(self, key: str) -> bool: ...
```

### Safety & Boundary Controls
- **Path Traversal Defense:** Every object key is sanitized via `sanitize_key(key)`. Keys containing null bytes, absolute paths, or directory traversal components (`..`) are rejected immediately with `ValueError`.
- **Atomic Operations:** Local file storage writes to unique staging files via `NamedTemporaryFile`, flushes and `fsync`s the stream, and performs an atomic POSIX `replace`.
- **Strict File Permissions:** Staged and published local files are explicitly granted private user-only permissions (`0600`).
- **Bounded Resource Usage:** Payloads and reads are bounded to a maximum object ceiling (default 16 MiB) to prevent unbounded buffer consumption.

## Supported Adapters

### 1. `LocalStorageAdapter`
- **Default for local development and test execution.**
- Backed by the local filesystem under `SHAPEOPS_DATA_DIR/storage` (default: `.runtime/storage`).
- Operates completely offline without cloud credentials, subscriptions, or network access.
- Confines all operations strictly within the configured storage root.

### 2. `AzureBlobStorageAdapter`
- **Production cloud adapter designed for Azure Container Apps.**
- Connects to Azure Blob Storage using Azure Managed Identity (`DefaultAzureCredential`) rather than static storage account keys or SAS tokens.
- Lazy imports Azure SDK dependencies (`azure-storage-blob` and `azure-identity`), ensuring that local developer and testing workstations do not require Azure packages.
- Zero billable API calls or resource allocation occurs during local execution or unconfigured runtime.

## Environment Configuration

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `SHAPEOPS_STORAGE_TYPE` | `local` | Selects adapter implementation (`local` or `azure`). |
| `SHAPEOPS_DATA_DIR` | `.runtime` | Root directory for local storage and SQLite databases. |
| `SHAPEOPS_AZURE_STORAGE_URL` | — | Blob service endpoint (`https://<account>.blob.core.windows.net`). |
| `SHAPEOPS_AZURE_CONTAINER` | `shapeops-artifacts` | Target container name within the storage account. |
