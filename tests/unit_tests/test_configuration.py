"""Check deployment configuration without importing retrieval backends."""

import ast
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / "langgraph.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("graph", CONFIG["graphs"].values())
def test_graph_entrypoint_exists(graph):
    relative_path, symbol = graph.split(":")
    tree = ast.parse((ROOT / relative_path).read_text(encoding="utf-8"))
    assignments = {
        target.id
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    assert symbol in assignments


def test_environment_example_covers_runtime_configuration():
    assert CONFIG["env"] == ".env"
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    names = {
        line.split("=", 1)[0]
        for line in example.splitlines()
        if line and not line.startswith("#") and "=" in line
    }
    assert {
        "DASHSCOPE_API_KEY", "EMBEDDING_MODEL", "VECTORSTORE_PATH",
        "ELASTICSEARCH_URL", "CHAT_MODEL",
    } <= names
    assert "DASHSCOPE_API_KEY=\n" in example


def test_application_sources_do_not_contain_provider_keys():
    paths = list((ROOT / "src").rglob("*.py"))
    paths += list((ROOT / "xiaomi_entity").rglob("*.py"))
    paths += list(ROOT.glob("*.py"))
    for path in paths:
        assert not re.search(
            r"\bsk-[A-Za-z0-9_-]{20,}", path.read_text(encoding="utf-8")
        ), f"Potential credential in {path.relative_to(ROOT)}"
