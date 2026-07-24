import pytest
from openai import AsyncOpenAI

from app.openai_client import get_model, get_openai


@pytest.fixture(autouse=True)
def _clear_cache():
    get_openai.cache_clear()
    yield
    get_openai.cache_clear()


def test_get_openai_raises_when_key_missing(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        get_openai()


def test_get_openai_returns_async_client_when_key_set(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert isinstance(get_openai(), AsyncOpenAI)


def test_get_openai_is_cached(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert get_openai() is get_openai()


def test_get_model_defaults_to_latest(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    assert get_model() == "gpt-5.6-terra"


def test_get_model_respects_env_override(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    assert get_model() == "gpt-4o"
