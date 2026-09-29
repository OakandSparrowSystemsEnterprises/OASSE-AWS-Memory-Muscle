from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from continuity_mvp.demo import run


def main() -> int:
    rows = run()
    print("\nCONTINUITY MVP\n")
    print("One authoritative lineage. Replaceable model substrates.\n")
    for i, row in enumerate(rows, start=1):
        print(f"Step {i}: {row['model']}")
        print(f"  decision: {row['decision']}")
        print(f"  revision: {row['revision_before']} -> {row['revision_after']}")
        print(f"  state:    {row['state_digest']}")
        inv = row.get("invariant", {})
        print(f"  continuity score: {inv.get('continuity_score')}")
        print(f"  reason: {row['reason']}\n")
    print("Expected proof: first two handoffs advance the SAME lineage; the third")
    print("attempts to delete unresolved state and is denied without changing the state.\n")
    print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
