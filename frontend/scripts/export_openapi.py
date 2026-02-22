from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def main() -> None:
    from sift.main import app

    output_path = Path(__file__).resolve().parent.parent / "openapi.json"
    output_path.write_text(json.dumps(app.openapi(), indent=2), encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
