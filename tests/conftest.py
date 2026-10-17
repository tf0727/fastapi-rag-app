"""Load the real HTTP application without model downloads or provider calls."""

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import Mock

import dotenv
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage


@pytest.fixture
def api_module(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root))
    import src.agent as agent_package

    def respond(value):
        return {"messages": value["messages"] + [AIMessage(content="test answer")]}

    graph = Mock()
    graph.invoke.side_effect = respond
    retriever = types.ModuleType("src.agent.retriever8")
    retriever.app = graph
    retriever.extract_text_content = str
    monkeypatch.setitem(sys.modules, "src.agent.retriever8", retriever)
    monkeypatch.setattr(agent_package, "retriever8", retriever, raising=False)
    # Tests must never read developer credentials from a real .env file.
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)
    monkeypatch.setenv("MAX_HISTORY_MESSAGES", "4")
    path = root / "main.py"
    spec = importlib.util.spec_from_file_location("xiaomi_api_under_test", path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def client(api_module):
    with TestClient(api_module.app) as test_client:
        yield test_client
