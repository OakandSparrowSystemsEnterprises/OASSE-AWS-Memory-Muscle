from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
required = [
    "README.md",
    "NOTICE.md",
    "config/runtime-manifest.json",
    "schemas/action-envelope.schema.json",
    "schemas/learning-event.schema.json",
    "src/oasse_memory_muscle/contracts.py",
    "src/oasse_memory_muscle/boundary.py",
    "docs/ARCHITECTURE.md",
    "rocketride/README.md",
]

missing = [path for path in required if not (ROOT / path).exists()]
if missing:
    raise SystemExit(f"missing skeleton files: {missing}")

manifest = json.loads((ROOT / "config/runtime-manifest.json").read_text())
assert manifest["authority"]["authoritative"] is True
assert all(not plane["authoritative"] for plane in manifest["planes"].values())
print("skeleton OK")
