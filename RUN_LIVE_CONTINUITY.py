from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from continuity_mvp.live_demo import run_live


REQUIRED = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GEMINI_API_KEY",
    "xai": "XAI_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}


def main() -> int:
    order = [x.strip() for x in os.getenv("CONTINUITY_PROVIDER_ORDER", "openai,anthropic,google").split(",") if x.strip()]
    missing = [REQUIRED[p] for p in order if p in REQUIRED and not os.getenv(REQUIRED[p])]
    if missing:
        print("Missing API credentials for the selected provider order:")
        for key in missing:
            print(f"  {key}")
        print("\nSet those environment variables and rerun this file.")
        return 2
    print(json.dumps(run_live(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
