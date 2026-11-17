"""One LLM provider behind a small protocol, plus a fake for tests."""
from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.config import Settings

TIMEOUT_SECONDS = 30.0
MAX_OUTPUT_TOKENS = 8000

# JSON-schema keywords Structured Outputs may reject. Our own pydantic model re-checks every one of them.
_UNSUPPORTED = {"minLength", "maxLength", "minItems", "maxItems", "title", "default", "minimum", "maximum",
                "exclusiveMinimum", "exclusiveMaximum", "pattern", "format"}


class LLMError(Exception):
    """Timeout, refusal, API error or unusable response."""


class LLMClient(Protocol):
    model: str

    def generate_json(self, system: str, user: str, schema: dict) -> dict: ...


def to_output_schema(schema: dict) -> dict:
    """Make a pydantic JSON schema acceptable for structured outputs: closed objects, no size keywords."""

    def walk(node):
        if isinstance(node, list):
            return [walk(x) for x in node]
        if not isinstance(node, dict):
            return node
        out = {}
        for key, value in node.items():
            if key == "properties" or key == "$defs":  # names of fields are data, not keywords
                out[key] = {name: walk(sub) for name, sub in value.items()}
            elif key in _UNSUPPORTED:
                continue
            else:
                out[key] = walk(value)
        if out.get("type") == "object":
            out["additionalProperties"] = False
        return out

    return walk(schema)


class AnthropicLLM:
    """Claude via the official SDK, constrained to the report schema with structured outputs."""

    def __init__(self, api_key: str, model: str, timeout: float = TIMEOUT_SECONDS):
        import anthropic  # imported lazily so tests and the core never need the SDK

        self.model = model
        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=api_key or None, timeout=timeout, max_retries=1)

    def generate_json(self, system: str, user: str, schema: dict) -> dict:
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=MAX_OUTPUT_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_config={"effort": "low",
                               "format": {"type": "json_schema", "schema": to_output_schema(schema)}},
            )
        except self._anthropic.APIError as e:
            raise LLMError(f"{type(e).__name__}: {e}") from e
        if response.stop_reason == "refusal":
            raise LLMError("model refused the request")
        if response.stop_reason == "max_tokens":
            raise LLMError("response truncated at max_tokens")
        text = next((b.text for b in response.content if b.type == "text"), None)
        if text is None:
            raise LLMError("no text block in response")
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise LLMError(f"invalid JSON from model: {e}") from e


DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"
# The free tier is a small daily quota per model, so a report falls through to the lighter models.
DEFAULT_GEMINI_FALLBACKS = ("gemini-3.1-flash-lite", "gemini-3.5-flash-lite")
GEMINI_API_VERSION = "v1beta"
TRANSIENT_CODES = {429, 500, 502, 503, 504}  # busy or overloaded: worth a short wait, not a guardrail retry
TRANSPORT_ATTEMPTS = 3
BACKOFF_SECONDS = 2.0
QUOTA_COOLDOWN_SECONDS = 3600.0  # how long an out-of-quota model is skipped before it is tried again
BUSY_COOLDOWN_SECONDS = 300.0  # an overloaded (503) or timing-out model is skipped for a few minutes
DEFAULT_ANTHROPIC_MODEL = "claude-opus-5-5"


def _is_quota_error(e: Exception) -> bool:
    return getattr(e, "code", None) == 429 and "quota" in str(e).lower()


def _is_busy_error(e: Exception) -> bool:
    """Overloaded, rate-limited (not out of quota) or timed out: another model may well answer right now."""
    if _is_quota_error(e):
        return False
    return getattr(e, "code", None) in TRANSIENT_CODES or "timeout" in type(e).__name__.lower()


class GeminiLLM:
    """Gemini via the google-genai SDK, constrained to the report schema with JSON-schema output.

    `model` is the model that answered the last call: it moves down `models` when one runs out of quota.
    """

    def __init__(self, api_key: str, model: str, timeout: float = TIMEOUT_SECONDS, client=None, sleep=time.sleep,
                 fallback_models: tuple[str, ...] = (), clock=time.monotonic):
        self.models = (model, *[m for m in fallback_models if m and m != model])
        self.model = model
        self._exhausted_until: dict[str, float] = {}
        self._clock = clock
        self._sleep = sleep
        self._timeout_ms = int(timeout * 1000)
        if client is None:
            from google import genai  # imported lazily so tests and the core never need the SDK
            from google.genai import types

            # System instructions are only accepted on v1beta ("Developer instruction is not enabled for api version v1").
            client = genai.Client(api_key=api_key, http_options=types.HttpOptions(api_version=GEMINI_API_VERSION))
        self._client = client

    def generate_json(self, system: str, user: str, schema: dict) -> dict:
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_json_schema=to_output_schema(schema),
            http_options=types.HttpOptions(timeout=self._timeout_ms),
        )
        now = self._clock()
        available = [m for m in self.models if self._exhausted_until.get(m, 0.0) <= now] or list(self.models)
        last: Exception | None = None
        for i, model in enumerate(available):
            has_next = i < len(available) - 1
            try:
                # With another model to fall back on, a busy model is not waited for: move on at once.
                response = self._call(model, user, config, attempts=1 if has_next else TRANSPORT_ATTEMPTS)
            except Exception as e:
                last = e
                if has_next and _is_quota_error(e):
                    self._exhausted_until[model] = now + QUOTA_COOLDOWN_SECONDS
                    continue
                if has_next and _is_busy_error(e):
                    self._exhausted_until[model] = now + BUSY_COOLDOWN_SECONDS
                    continue
                raise LLMError(f"{type(e).__name__}: {e}") from e
            self._exhausted_until.pop(model, None)
            self.model = model
            return self._parse(response)
        raise LLMError(f"{type(last).__name__}: {last}")  # pragma: no cover - the loop always returns or raises

    def _call(self, model: str, user: str, config, attempts: int = TRANSPORT_ATTEMPTS):
        for attempt in range(attempts):
            try:
                return self._client.models.generate_content(model=model, contents=user, config=config)
            except Exception as e:
                transient = getattr(e, "code", None) in TRANSIENT_CODES and not _is_quota_error(e)
                if transient and attempt < attempts - 1:
                    self._sleep(BACKOFF_SECONDS * (attempt + 1))
                    continue
                raise

    @staticmethod
    def _parse(response) -> dict:
        text = getattr(response, "text", None)
        if not text:
            raise LLMError("empty response from model")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise LLMError(f"invalid JSON from model: {e}") from e
        if not isinstance(data, dict):
            raise LLMError("model returned JSON that is not an object")
        return data


def build_llm(settings: Settings) -> LLMClient | None:
    """The configured provider, or None when no key is set (the API then answers 503 for AI reports)."""
    provider = settings.llm_provider.strip().lower()
    if provider and provider not in ("gemini", "anthropic"):
        raise ValueError(f"LLM_PROVIDER must be 'gemini' or 'anthropic', got {provider!r}")
    if not provider:
        provider = "gemini" if settings.gemini_api_key else "anthropic" if settings.llm_api_key else ""
    if provider == "gemini":
        if not settings.gemini_api_key:
            raise ValueError("LLM_PROVIDER=gemini but GEMINI_API_KEY is not set")
        raw = settings.llm_fallback_models
        fallbacks = DEFAULT_GEMINI_FALLBACKS if raw is None else tuple(m.strip() for m in raw.split(",") if m.strip())
        return GeminiLLM(settings.gemini_api_key, settings.llm_model or DEFAULT_GEMINI_MODEL, fallback_models=fallbacks)
    if provider == "anthropic":
        if not settings.llm_api_key:
            raise ValueError("LLM_PROVIDER=anthropic but LLM_API_KEY is not set")
        return AnthropicLLM(settings.llm_api_key, settings.llm_model or DEFAULT_ANTHROPIC_MODEL)
    return None


class FakeLLM:
    """Scripted responses for tests. An Exception instance is raised; the last response repeats."""

    model = "fake-llm"

    def __init__(self, responses: list):
        self._responses = list(responses)
        self.calls: list[tuple[str, str, dict]] = []

    def generate_json(self, system: str, user: str, schema: dict):
        self.calls.append((system, user, schema))
        r = self._responses.pop(0) if len(self._responses) > 1 else self._responses[0]
        if isinstance(r, Exception):
            raise r
        return r
