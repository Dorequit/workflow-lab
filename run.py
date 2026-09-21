"""Run the local SignalDesk demo or print a sample workflow result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from workflow_lab.engine import run_workflow
from workflow_lab.server import serve


def main() -> None:
    parser = argparse.ArgumentParser(description="SignalDesk incident workflow")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: localhost)")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port (default: 8000)")
    parser.add_argument("--demo", action="store_true", help="Print the checkout sample as JSON")
    args = parser.parse_args()

    if args.demo:
        sample = Path(__file__).parent / "examples" / "checkout-outage.json"
        result = run_workflow(json.loads(sample.read_text(encoding="utf-8")))
        # ASCII-safe output also works in Windows terminals using legacy encodings.
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return

    serve(args.host, args.port)


if __name__ == "__main__":
    main()
