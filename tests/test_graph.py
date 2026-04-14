import json
import pytest

from src.graph import process_resumes_tool, query_candidates_tool


def test_process_resumes_tool_missing_directory():
    result = process_resumes_tool.invoke({"folder_path": "/nonexistent/path"})
    assert "not found" in result


def test_process_resumes_tool_success(monkeypatch, tmp_path):
    resumes_dir = tmp_path / "resumes"
    resumes_dir.mkdir()

    calls = []
    monkeypatch.setattr("src.graph.process_resumes", lambda path: calls.append(path))

    result = process_resumes_tool.invoke({"folder_path": str(resumes_dir)})
    assert "Processing complete" in result
    assert len(calls) == 1


def test_query_candidates_tool_all(monkeypatch):
    fake = [{"id": 1, "name": "Alice"}]
    monkeypatch.setattr("src.graph.get_all_candidates", lambda: fake)

    result = json.loads(query_candidates_tool.invoke({}))
    assert result["count"] == 1
    assert result["candidates"][0]["name"] == "Alice"


def test_query_candidates_tool_by_ids(monkeypatch):
    fake = [{"id": 2, "name": "Bob"}]
    monkeypatch.setattr("src.graph.get_candidates_by_ids", lambda ids: fake)

    result = json.loads(query_candidates_tool.invoke({"candidate_ids": [2]}))
    assert result["count"] == 1
    assert result["candidates"][0]["name"] == "Bob"


def test_query_candidates_tool_by_names(monkeypatch):
    fake = [{"id": 3, "name": "Charlie"}]
    monkeypatch.setattr("src.graph.get_candidates_by_names", lambda names: fake)

    result = json.loads(query_candidates_tool.invoke({"names": ["Charlie"]}))
    assert result["count"] == 1


def test_query_candidates_tool_empty(monkeypatch):
    monkeypatch.setattr("src.graph.get_all_candidates", lambda: [])

    result = json.loads(query_candidates_tool.invoke({}))
    assert result["candidates"] == []
    assert "No candidates" in result["message"]
