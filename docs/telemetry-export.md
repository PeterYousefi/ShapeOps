# Retained local telemetry export

Trusted operators can preserve actual retained inference metadata before local retention removes it:

```sh
.venv/bin/python -m backend.export_telemetry \
  --database .runtime/telemetry.sqlite \
  --output /existing/private/directory/shapeops-telemetry.json
```

The output parent must exist. The command opens the database read-only, uses one SQLite transaction for requests and screening evidence, and does not import/start the application, initialize training, prune records or migrate schemas. Missing/nonregular inputs fail without creating a database. A legacy database without screening has `screening_available: false` and null screening records; nothing is backfilled.

Schema version 1 contains actual request metadata and matching saved geometry screening, selected newest first (timestamp, then request ID), at most 1,000 requests in the seven-day window ending at `captured_at`, inclusive. Future timestamps are excluded. The selection policy is embedded in the file. This is a bounded retention snapshot, not all-time history. The origin explicitly identifies local inference telemetry; sample/upload sources remain separate. No raw CAD, meshes, per-face geometry, filenames, authentication tokens, host paths or training estimators are exported. Request IDs, model identities, timing and aggregate geometry still require appropriate handling.

Saved request values and screening contracts are validated. Mismatched identity/model/source/OOD, corrupt reference summaries, oversized text or screening JSON fail the whole export. Screening JSON is capped at 16 KiB per observation, request text fields at 1 KiB each and the complete JSON at 8 MiB. Failures do not publish partial evidence. The trusted local database is not treated as a hostile query execution sandbox; locks use a two-second SQLite busy timeout.

Publication uses a same-directory temporary file with mode 0600, flush/fsync, and an atomic no-overwrite hard link. Existing files, symlinks and earlier evidence are preserved. Temporary files are cleaned on handled failures; abrupt host/process failure can leave a private staging file. The output filesystem must support hard links. File data is synchronized, but directory durability across power loss is not guaranteed. CLI stdout reports the actual SHA-256, byte count and exported record count; it does not print the records or filesystem paths on failure.

This is an explicit operator export, not automatic background archival, signed evidence, client-side encryption, or a production usage assertion. Do not commit exported telemetry to the public repository. No public API, privileged action, or deployment is introduced.

## Storage adapter archival

In addition to writing to an explicit local output file, operators can archive snapshots directly to the configured storage adapter (such as POSIX local storage or Azure Blob Storage via Managed Identity):

```sh
# Archive snapshot to configured adapter with default prefix telemetry/snapshots/
.venv/bin/python -m backend.export_telemetry \
  --database .runtime/telemetry.sqlite \
  --archive

# Archive snapshot with custom prefix
.venv/bin/python -m backend.export_telemetry \
  --database .runtime/telemetry.sqlite \
  --archive \
  --prefix telemetry/audit-runs
```

When `--archive` is invoked, `archive_snapshot()` validates and formats the retained snapshot, creates an immutable key format (`<prefix>/<timestamp>_<sha16>.json`), and persists it through `backend.storage.get_storage_adapter()`. The resulting key, SHA-256 digest, byte count, and record count are reported on stdout.
