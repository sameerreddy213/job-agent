"""Dump the OpenAPI schema to openapi.json (no server/DB connection needed).

Run from the backend/ directory:
    python scripts/export_openapi.py
"""
import json
import pathlib
import sys

# Ensure the backend root is importable when run as a script.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402


def main() -> None:
    schema = app.openapi()
    out = pathlib.Path("openapi.json")
    out.write_text(json.dumps(schema, indent=2))
    paths = len(schema.get("paths", {}))
    print(f"[openapi] wrote {out} ({paths} paths).")


if __name__ == "__main__":
    main()
