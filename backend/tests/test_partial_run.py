"""'Test node' slicing: run only a node and its ancestors."""

import pytest

from app.engine.executor import execute_workflow, slice_to_node
from app.engine.registry import get_registry
from app.engine.types import WorkflowError


@pytest.fixture(scope="module")
def registry():
    return get_registry()


DEFINITION = {
    "nodes": [
        {"id": "start", "type": "manual_trigger", "config": {"payload": '{"n": 1}'}},
        {"id": "a", "type": "set_variable", "config": {"variables": '{"a": 1}'}},
        {"id": "b", "type": "set_variable", "config": {"variables": '{"b": 2}'}},
        {"id": "c", "type": "set_variable", "config": {"variables": '{"c": 3}'}},
    ],
    "edges": [
        {"source": "start", "target": "a"},
        {"source": "a", "target": "b"},
        {"source": "start", "target": "c"},
    ],
}


def test_slice_keeps_target_and_ancestors_only():
    sliced = slice_to_node(DEFINITION, "b")
    ids = {n["id"] for n in sliced["nodes"]}
    assert ids == {"start", "a", "b"}
    assert all(e["source"] in ids and e["target"] in ids for e in sliced["edges"])


def test_slice_trigger_only():
    sliced = slice_to_node(DEFINITION, "start")
    assert {n["id"] for n in sliced["nodes"]} == {"start"}
    assert sliced["edges"] == []


def test_slice_unknown_node_rejected():
    with pytest.raises(WorkflowError, match="not part of the workflow"):
        slice_to_node(DEFINITION, "ghost")


async def test_sliced_run_executes_only_the_branch(registry):
    result = await execute_workflow(slice_to_node(DEFINITION, "b"), registry)
    assert result["status"] == "success"
    assert set(result["outputs"]) == {"start", "a", "b"}
    assert "c" not in result["node_statuses"]
