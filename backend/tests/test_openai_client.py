import pytest
from openai import AsyncOpenAI

from app.openai_client import get_extractor_model, get_openai, get_planner_model


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


def test_get_planner_model_returns_env_value(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL_PLANNER", "gpt-5.6-sol")
    assert get_planner_model() == "gpt-5.6-sol"


def test_get_planner_model_raises_when_unset(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL_PLANNER", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_MODEL_PLANNER"):
        get_planner_model()


def test_get_extractor_model_returns_env_value(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL_EXTRACTOR", "gpt-5.6-terra")
    assert get_extractor_model() == "gpt-5.6-terra"


def test_get_extractor_model_raises_when_unset(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL_EXTRACTOR", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_MODEL_EXTRACTOR"):
        get_extractor_model()
