"""Exercise the in-memory history limits and snapshots."""

from langchain_core.messages import AIMessage, HumanMessage


def test_history_limit_keeps_recent_messages(api_module):
    store = api_module.SessionStore()
    messages = [HumanMessage(content=str(index)) for index in range(6)]
    store.append("session", messages)
    assert [message.content for message in store.history("session")] == [
        "2", "3", "4", "5"
    ]


def test_snapshot_does_not_expose_mutable_history(api_module):
    store = api_module.SessionStore()
    store.append("one", [HumanMessage(content="question"), AIMessage(content="answer")])
    snapshot = store.snapshot("one")
    assert snapshot == [
        {"role": "user", "content": "question"},
        {"role": "assistant", "content": "answer"},
    ]
    snapshot[0]["content"] = "changed"
    assert store.snapshot("one")[0]["content"] == "question"
    assert store.snapshot("two") == []


def test_clear_reports_whether_session_existed(api_module):
    store = api_module.SessionStore()
    store.append("one", [HumanMessage(content="question")])
    assert store.clear("one") is True
    assert store.clear("one") is False
    assert store.snapshot("one") == []
