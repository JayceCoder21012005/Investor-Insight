import json
from types import SimpleNamespace

import pytest

from app.ai.llm import AnthropicLLM, GeminiLLM, LLMError, build_llm
from app.config import Settings


def settings(**kw) -> Settings:
    base = dict(gemini_api_key="", llm_api_key="", llm_provider="", llm_model="", _env_file=None)
    return Settings(**{**base, **kw})


# ---------------------------------------------------------------- provider selection
def test_no_key_means_no_llm():
    assert build_llm(settings()) is None


def test_gemini_key_selects_gemini_with_a_default_model():
    llm = build_llm(settings(gemini_api_key="k"))
    assert isinstance(llm, GeminiLLM) and llm.model.startswith("gemini")


def test_llm_model_overrides_the_default():
    assert build_llm(settings(gemini_api_key="k", llm_model="gemini-x")).model == "gemini-x"


def test_anthropic_key_selects_anthropic():
    llm = build_llm(settings(llm_api_key="k"))
    assert isinstance(llm, AnthropicLLM) and llm.model.startswith("claude")


def test_explicit_provider_wins_when_both_keys_exist():
    s = settings(gemini_api_key="g", llm_api_key="a", llm_provider="anthropic")
    assert isinstance(build_llm(s), AnthropicLLM)
    assert isinstance(build_llm(settings(gemini_api_key="g", llm_api_key="a")), GeminiLLM)


def test_provider_without_its_key_is_an_error_not_a_silent_none():
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        build_llm(settings(llm_provider="gemini"))


def test_unknown_provider_is_an_error():
    with pytest.raises(ValueError):
        build_llm(settings(llm_provider="nope", gemini_api_key="k"))


# ---------------------------------------------------------------- Gemini wrapper (no network)
class FakeGenAI:
    def __init__(self, text=None, exc=None):
        self.calls = []
        self._text, self._exc = text, exc
        self.models = SimpleNamespace(generate_content=self._generate)

    def _generate(self, **kwargs):
        self.calls.append(kwargs)
        if self._exc:
            raise self._exc
        return SimpleNamespace(text=self._text)


SCHEMA = {"type": "object", "title": "X", "properties": {"title": {"type": "string", "maxLength": 5}}}


def test_gemini_sends_system_prompt_user_prompt_and_a_json_schema():
    client = FakeGenAI(text='{"a": 1}')
    llm = GeminiLLM("k", "gemini-test", client=client)
    assert llm.generate_json("SYS", "USER", SCHEMA) == {"a": 1}
    call = client.calls[0]
    assert call["model"] == "gemini-test" and call["contents"] == "USER"
    cfg = call["config"]
    assert cfg.system_instruction == "SYS" and cfg.response_mime_type == "application/json"
    sent = cfg.response_json_schema
    assert "maxLength" not in json.dumps(sent) and sent["additionalProperties"] is False


def test_gemini_client_is_built_on_the_api_version_that_allows_system_instructions():
    from app.ai.llm import GEMINI_API_VERSION

    assert GEMINI_API_VERSION == "v1beta"
    client = GeminiLLM("k", "m")._client  # constructing the SDK client makes no network call
    assert client._api_client._http_options.api_version == "v1beta"


@pytest.mark.parametrize("text", [None, "", "not json", "[1, 2]"])
def test_gemini_unusable_responses_raise_llm_error(text):
    with pytest.raises(LLMError):
        GeminiLLM("k", "m", client=FakeGenAI(text=text)).generate_json("s", "u", SCHEMA)


class HttpError(Exception):
    def __init__(self, code):
        super().__init__(f"{code} error")
        self.code = code


class FlakyGenAI(FakeGenAI):
    def __init__(self, failures, text='{"ok": true}'):
        super().__init__(text=text)
        self._failures = list(failures)

    def _generate(self, **kwargs):
        self.calls.append(kwargs)
        if self._failures:
            raise self._failures.pop(0)
        return SimpleNamespace(text=self._text)


def test_transient_503_and_429_are_retried_with_backoff_before_giving_up():
    sleeps = []
    client = FlakyGenAI([HttpError(503), HttpError(429)])
    llm = GeminiLLM("k", "m", client=client, sleep=sleeps.append)
    assert llm.generate_json("s", "u", SCHEMA) == {"ok": True}
    assert len(client.calls) == 3 and len(sleeps) == 2 and sleeps[1] > sleeps[0]


def test_persistent_transient_errors_raise_after_the_limit():
    client = FlakyGenAI([HttpError(503)] * 5)
    llm = GeminiLLM("k", "m", client=client, sleep=lambda s: None)
    with pytest.raises(LLMError, match="503"):
        llm.generate_json("s", "u", SCHEMA)
    assert len(client.calls) == 3


def test_client_errors_are_not_retried():
    client = FlakyGenAI([HttpError(400)])
    llm = GeminiLLM("k", "m", client=client, sleep=lambda s: None)
    with pytest.raises(LLMError, match="400"):
        llm.generate_json("s", "u", SCHEMA)
    assert len(client.calls) == 1


class QuotaError(HttpError):
    def __init__(self):
        super().__init__(429)
        self.args = ("429 RESOURCE_EXHAUSTED. You exceeded your current quota",)


def test_quota_exhaustion_switches_to_the_next_model_without_waiting():
    sleeps = []
    client = FlakyGenAI([QuotaError()])
    llm = GeminiLLM("k", "main", client=client, sleep=sleeps.append, fallback_models=("lite",))
    assert llm.generate_json("s", "u", SCHEMA) == {"ok": True}
    assert [c["model"] for c in client.calls] == ["main", "lite"] and sleeps == []
    assert llm.model == "lite"  # the report records the model that actually answered


def test_an_exhausted_model_is_skipped_until_the_cooldown_ends():
    now = [0.0]
    client = FlakyGenAI([QuotaError()])
    llm = GeminiLLM("k", "main", client=client, sleep=lambda s: None, fallback_models=("lite",),
                    clock=lambda: now[0])
    llm.generate_json("s", "u", SCHEMA)
    llm.generate_json("s", "u", SCHEMA)
    assert [c["model"] for c in client.calls] == ["main", "lite", "lite"]
    now[0] += 3601
    llm.generate_json("s", "u", SCHEMA)
    assert client.calls[-1]["model"] == "main" and llm.model == "main"


def test_all_models_exhausted_raises_llm_error():
    client = FlakyGenAI([QuotaError(), QuotaError()])
    llm = GeminiLLM("k", "main", client=client, sleep=lambda s: None, fallback_models=("lite",))
    with pytest.raises(LLMError, match="quota"):
        llm.generate_json("s", "u", SCHEMA)
    assert len(client.calls) == 2


def test_an_overloaded_model_falls_over_to_the_next_without_waiting():
    sleeps = []
    client = FlakyGenAI([HttpError(503)])
    llm = GeminiLLM("k", "main", client=client, sleep=sleeps.append, fallback_models=("lite",))
    assert llm.generate_json("s", "u", SCHEMA) == {"ok": True}
    assert [c["model"] for c in client.calls] == ["main", "lite"] and sleeps == []
    assert llm.model == "lite"


def test_a_timeout_also_falls_over_to_the_next_model():
    class ReadTimeout(Exception):
        pass

    client = FlakyGenAI([ReadTimeout("timed out")])
    llm = GeminiLLM("k", "main", client=client, sleep=lambda s: None, fallback_models=("lite",))
    assert llm.generate_json("s", "u", SCHEMA) == {"ok": True}
    assert [c["model"] for c in client.calls] == ["main", "lite"]


def test_a_busy_model_is_skipped_for_a_short_cooldown_only():
    from app.ai.llm import BUSY_COOLDOWN_SECONDS

    now = [0.0]
    client = FlakyGenAI([HttpError(503)])
    llm = GeminiLLM("k", "main", client=client, sleep=lambda s: None, fallback_models=("lite",),
                    clock=lambda: now[0])
    llm.generate_json("s", "u", SCHEMA)
    llm.generate_json("s", "u", SCHEMA)
    assert [c["model"] for c in client.calls] == ["main", "lite", "lite"]
    assert BUSY_COOLDOWN_SECONDS < 3600
    now[0] += BUSY_COOLDOWN_SECONDS + 1
    llm.generate_json("s", "u", SCHEMA)
    assert client.calls[-1]["model"] == "main"


def test_the_last_model_still_retries_with_backoff_when_busy():
    sleeps = []
    client = FlakyGenAI([HttpError(503), HttpError(503), HttpError(503)])
    llm = GeminiLLM("k", "main", client=client, sleep=sleeps.append, fallback_models=("lite",))
    assert llm.generate_json("s", "u", SCHEMA) == {"ok": True}
    assert [c["model"] for c in client.calls] == ["main", "lite", "lite", "lite"] and len(sleeps) == 2


def test_fallback_models_come_from_settings():
    llm = build_llm(settings(gemini_api_key="k", llm_model="a", llm_fallback_models="b, c"))
    assert llm.models == ("a", "b", "c")
    assert build_llm(settings(gemini_api_key="k", llm_model="a", llm_fallback_models="")).models == ("a",)
    default = build_llm(settings(gemini_api_key="k"))
    assert len(default.models) > 1  # the free tier runs out per model, so there is a default chain


def test_gemini_api_exceptions_are_wrapped():
    with pytest.raises(LLMError, match="boom"):
        GeminiLLM("k", "m", client=FakeGenAI(exc=RuntimeError("boom"))).generate_json("s", "u", SCHEMA)


# ---------------------------------------------------------------- database URLs
def test_direct_url_is_derived_by_dropping_the_pooler_suffix():
    s = settings(database_url="postgresql://u:p@ep-cool-123-pooler.c-3.aws.neon.tech/neondb?sslmode=require")
    assert s.direct_database_url == "postgresql://u:p@ep-cool-123.c-3.aws.neon.tech/neondb?sslmode=require"


def test_explicit_direct_url_wins():
    s = settings(database_url="postgresql://u:p@ep-a-pooler.x/db", database_url_direct="postgresql://u:p@other/db")
    assert s.direct_database_url == "postgresql://u:p@other/db"


def test_non_neon_urls_are_left_alone():
    assert settings(database_url="sqlite:///x.db").direct_database_url == "sqlite:///x.db"


def test_the_test_suite_cannot_see_real_credentials_from_dotenv():
    s = Settings()  # reads backend/.env like production would, but conftest blanked the variables
    assert s.gemini_api_key == "" and s.database_url == ""
