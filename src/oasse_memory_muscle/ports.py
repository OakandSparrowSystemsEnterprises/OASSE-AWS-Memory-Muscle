from __future__ import annotations

from typing import Any, Protocol

from .contracts import ActionEnvelope, AuthorityDecision, LearningEvent


class SemanticMemoryPort(Protocol):
    def remember(self, text: str) -> str: ...
    def recall(self, query: str) -> list[str]: ...


class DurableGraphPort(Protocol):
    def store_learning_event(self, event: LearningEvent) -> str: ...
    def related_context(self, failure_signature: str) -> list[dict[str, Any]]: ...


class LiveStatePort(Protocol):
    def load(self, run_id: str, rows: list[dict[str, Any]]) -> None: ...
    def query(self, sql: str) -> list[dict[str, Any]]: ...


class SandboxPort(Protocol):
    def run(self, command: str) -> tuple[int, str, str]: ...


class SecurityPort(Protocol):
    def scan(self, path: str) -> dict[str, Any]: ...


class ProcedureMemoryPort(Protocol):
    def capture(self, run_id: str, summary: str) -> str: ...
    def replay(self, reference: str, inputs: dict[str, Any]) -> dict[str, Any]: ...


class AuthorityPort(Protocol):
    def evaluate(self, action: ActionEnvelope) -> AuthorityDecision: ...


class EffectPort(Protocol):
    def execute(self, action: ActionEnvelope, decision: AuthorityDecision) -> dict[str, Any]: ...
