from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Protocol
from urllib import request, error

from .contracts import ContinuityState


SYSTEM_PROMPT = """You are one reasoning substrate temporarily carrying an existing cognitive lineage.
You do not own the lineage and may not rewrite history. Continue the active work from the supplied
ContinuityState. Return ONLY JSON with keys summary, append_items, supersessions, delete_item_ids.
append_items is a list of objects with kind, text, status, provenance. supersessions is a list of
objects with old_item_id and replacement using the same item fields plus supersedes. If evidence is
insufficient to resolve an open question, preserve it. Never manufacture authority."""


@dataclass(frozen=True)
class ModelResult:
    provider: str
    model: str
    text: str


class ModelAdapter(Protocol):
    provider: str
    model: str

    def complete(self, state: ContinuityState, instruction: str) -> ModelResult: ...


def render_state(state: ContinuityState) -> str:
    return json.dumps(state.canonical_dict(), ensure_ascii=False, sort_keys=True, indent=2)


def _json_post(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float = 60.0) -> dict[str, Any]:
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"provider HTTP {exc.code}: {detail}") from exc
    return json.loads(body)


@dataclass(frozen=True)
class OpenAIResponsesAdapter:
    model: str = "gpt-5.6-sol"
    api_key: str = ""
    provider: str = "openai"

    @classmethod
    def from_env(cls) -> "OpenAIResponsesAdapter":
        return cls(model=os.getenv("OPENAI_MODEL", "gpt-5.6-sol"), api_key=os.getenv("OPENAI_API_KEY", ""))

    def complete(self, state: ContinuityState, instruction: str) -> ModelResult:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        payload = {
            "model": self.model,
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": SYSTEM_PROMPT}]},
                {"role": "user", "content": [{"type": "input_text", "text": render_state(state) + "\n\nTASK:\n" + instruction}]},
            ],
        }
        data = _json_post("https://api.openai.com/v1/responses", payload, {"Authorization": f"Bearer {self.api_key}"})
        chunks: list[str] = []
        for item in data.get("output", []):
            for part in item.get("content", []):
                if part.get("type") in {"output_text", "text"} and isinstance(part.get("text"), str):
                    chunks.append(part["text"])
        if not chunks:
            raise RuntimeError("OpenAI response contained no text output")
        return ModelResult(self.provider, self.model, "\n".join(chunks))


@dataclass(frozen=True)
class AnthropicAdapter:
    model: str = "claude-opus-5"
    api_key: str = ""
    provider: str = "anthropic"

    @classmethod
    def from_env(cls) -> "AnthropicAdapter":
        return cls(model=os.getenv("ANTHROPIC_MODEL", "claude-opus-5"), api_key=os.getenv("ANTHROPIC_API_KEY", ""))

    def complete(self, state: ContinuityState, instruction: str) -> ModelResult:
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": render_state(state) + "\n\nTASK:\n" + instruction}],
        }
        data = _json_post(
            "https://api.anthropic.com/v1/messages",
            payload,
            {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
        )
        text = "\n".join(p.get("text", "") for p in data.get("content", []) if p.get("type") == "text")
        if not text:
            raise RuntimeError("Anthropic response contained no text output")
        return ModelResult(self.provider, self.model, text)


@dataclass(frozen=True)
class GeminiAdapter:
    model: str = "gemini-3.8-flash"
    api_key: str = ""
    provider: str = "google"

    @classmethod
    def from_env(cls) -> "GeminiAdapter":
        return cls(model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"), api_key=os.getenv("GEMINI_API_KEY", ""))

    def complete(self, state: ContinuityState, instruction: str) -> ModelResult:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": render_state(state) + "\n\nTASK:\n" + instruction}]}],
        }
        data = _json_post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            payload,
            {"x-goog-api-key": self.api_key},
        )
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("Gemini response contained no candidates")
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "\n".join(p.get("text", "") for p in parts if isinstance(p.get("text"), str))
        if not text:
            raise RuntimeError("Gemini response contained no text output")
        return ModelResult(self.provider, self.model, text)


@dataclass(frozen=True)
class OpenAICompatibleAdapter:
    provider: str
    base_url: str
    model: str
    api_key: str

    def complete(self, state: ContinuityState, instruction: str) -> ModelResult:
        if not self.api_key:
            raise RuntimeError(f"{self.provider} API key is not configured")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": render_state(state) + "\n\nTASK:\n" + instruction},
            ],
            "temperature": 0,
        }
        data = _json_post(self.base_url.rstrip("/") + "/chat/completions", payload, {"Authorization": f"Bearer {self.api_key}"})
        text = data["choices"][0]["message"]["content"]
        return ModelResult(self.provider, self.model, text)

    @classmethod
    def xai_from_env(cls) -> "OpenAICompatibleAdapter":
        return cls("xai", "https://api.x.ai/v1", os.getenv("XAI_MODEL", "grok-4.7"), os.getenv("XAI_API_KEY", ""))

    @classmethod
    def mistral_from_env(cls) -> "OpenAICompatibleAdapter":
        return cls("mistral", "https://api.mistral.ai/v1", os.getenv("MISTRAL_MODEL", "mistral-large-latest"), os.getenv("MISTRAL_API_KEY", ""))

    @classmethod
    def deepseek_from_env(cls) -> "OpenAICompatibleAdapter":
        return cls("deepseek", "https://api.deepseek.com", os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro"), os.getenv("DEEPSEEK_API_KEY", ""))
