from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SnykCliAdapter:
    executable: str = "snyk"

    def scan(self, path: str) -> dict[str, Any]:
        proc = subprocess.run(
            [self.executable, "code", "test", path, "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
        payload = proc.stdout.strip() or proc.stderr.strip()
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            parsed = {"raw": payload}
        return {"exit_code": proc.returncode, "result": parsed}


@dataclass(frozen=True)
class RoteCliAdapter:
    executable: str = "rote"

    def capture(self, run_id: str, summary: str) -> str:
        # Rote crystallization is deliberately operator-guided during the hackathon.
        # This returns the durable handoff payload instead of pretending a successful
        # method can be inferred without a recorded workspace trace.
        payload = {"run_id": run_id, "summary": summary}
        return json.dumps(payload, sort_keys=True)

    def replay(self, reference: str, inputs: dict[str, Any]) -> dict[str, Any]:
        args = [self.executable, "play", "run", reference, "--output=json", "--yes"]
        args.extend(f"{key}={value}" for key, value in inputs.items())
        proc = subprocess.run(args, capture_output=True, text=True, check=False)
        raw = proc.stdout.strip() or proc.stderr.strip()
        try:
            result: Any = json.loads(raw)
        except json.JSONDecodeError:
            result = {"raw": raw}
        return {"exit_code": proc.returncode, "result": result}


@dataclass(frozen=True)
class LocalSandboxAdapter:
    root: Path

    def run(self, command: str) -> tuple[int, str, str]:
        proc = subprocess.run(
            command,
            cwd=self.root,
            shell=True,
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.returncode, proc.stdout, proc.stderr
