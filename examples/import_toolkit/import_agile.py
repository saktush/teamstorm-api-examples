#!/usr/bin/env python3
import sys
from pathlib import Path

# Running this file directly (`python examples/import_toolkit/import_agile.py`) puts
# only examples/import_toolkit/ on sys.path[0]; add its parent so the sibling
# `import_toolkit` package below resolves regardless of the caller's cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from import_toolkit.workflows.imports.agile import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
