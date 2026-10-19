"""Disposable STEP parser; native diagnostics are never part of the result protocol."""

import json
from pathlib import Path
import sys
from backend.worker_limits import apply_limits, MAX_RESULT_BYTES

ERROR = "STEP could not be processed within supported geometry and resource limits."


def write_result(result, output):
    """Publish complete, finite JSON atomically with a bounded encoded byte count."""
    partial = output.with_suffix(".partial")
    try:
        total = 0
        with partial.open("xb") as stream:
            for chunk in json.JSONEncoder(
                allow_nan=False, separators=(",", ":")
            ).iterencode(result):
                data = chunk.encode("utf-8")
                total += len(data)
                if total > MAX_RESULT_BYTES:
                    raise ValueError("CAD result exceeds the output budget")
                stream.write(data)
        partial.replace(output)
    finally:
        partial.unlink(missing_ok=True)


def main():
    output = Path(sys.argv[2])
    try:
        apply_limits()
        import cadquery as cq
        from backend.cad import describe

        shape = cq.importers.importStep(sys.argv[1]).val()
        write_result(describe(shape), output)
    except Exception:
        try:
            write_result({"error": ERROR}, output)
        except Exception:
            pass  # The parent treats a missing/incomplete result as a safe rejection.
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
