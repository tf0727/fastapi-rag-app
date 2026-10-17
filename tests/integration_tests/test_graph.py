"""HTTP integration tests; the external RAG graph is replaced by a fixture."""

import uuid

import pytest


def test_health_and_api_documentation(client):
    assert client.get("/health").json() == {"status": "ok", "graph_loaded": True}
    assert client.get("/docs").status_code == 200
    assert "/chat" in client.get("/openapi.json").json()["paths"]


def test_single_turn_does_not_store_history(client, api_module):
    response = client.post("/ask", json={"question": " question ", "session_id": "one"})
    assert response.status_code == 200
    assert response.json()["answer"] == "test answer"
    messages = api_module.GRAPH.invoke.call_args.args[0]["messages"]
    assert messages[0].content == "question"
    assert client.get("/chat/history", params={"session_id": "one"}).json()["messages"] == []


def test_multi_turn_history_and_clear(client, api_module):
    first = client.post("/chat", json={"question": "first"})
    assert first.status_code == 200
    session = first.json()["session_id"]
    uuid.UUID(session)
    second = client.post("/chat", json={"question": "follow up", "session_id": session})
    assert second.status_code == 200
    assert second.json()["session_id"] == session
    passed_messages = api_module.GRAPH.invoke.call_args.args[0]["messages"]
    assert [message.content for message in passed_messages] == [
        "first", "test answer", "follow up"
    ]
    history = client.get("/chat/history", params={"session_id": session}).json()["messages"]
    assert [message["role"] for message in history] == ["user", "assistant"] * 2
    assert client.post("/chat/clear", json={"session_id": session}).json()["cleared"] is True
    assert client.get("/chat/history", params={"session_id": session}).json()["messages"] == []


@pytest.mark.parametrize("endpoint", ["/ask", "/chat"])
def test_blank_question_rejected_without_graph_call(client, api_module, endpoint):
    assert client.post(endpoint, json={"question": "  "}).status_code == 400
    assert client.post(endpoint, json={}).status_code == 422
    api_module.GRAPH.invoke.assert_not_called()


def test_graph_failure_rolls_back_current_user_message(client, api_module):
    client.post("/chat", json={"question": "first", "session_id": "one"})
    before = client.get("/chat/history", params={"session_id": "one"}).json()
    api_module.GRAPH.invoke.side_effect = RuntimeError("mock backend unavailable")
    assert client.post("/chat", json={"question": "second", "session_id": "one"}).status_code == 500
    assert client.get("/chat/history", params={"session_id": "one"}).json() == before
