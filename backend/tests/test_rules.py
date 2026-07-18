"""Wiring-rule and config-rule tests: the constraints that keep workflows sane."""

import pytest

from app.engine.executor import execute_workflow
from app.engine.fields import field_visible, missing_required
from app.engine.registry import get_registry
from app.engine.types import WorkflowError


@pytest.fixture(scope="module")
def registry():
    return get_registry()


def wf(nodes, edges):
    return {"nodes": nodes, "edges": edges}


def trigger(nid="start"):
    return {"id": nid, "type": "manual_trigger", "config": {}}


# ---------- wiring rules ----------


async def test_two_triggers_rejected(registry):
    with pytest.raises(WorkflowError, match="Only one trigger"):
        await execute_workflow(wf([trigger("a"), trigger("b")], []), registry)


async def test_edge_into_trigger_rejected(registry):
    with pytest.raises(WorkflowError, match="cannot receive connections"):
        await execute_workflow(
            wf(
                [
                    trigger(),
                    {"id": "vars", "type": "set_variable", "config": {"variables": "{}"}},
                ],
                [
                    {"source": "start", "target": "vars"},
                    {"source": "vars", "target": "start"},
                ],
            ),
            registry,
        )


async def test_unknown_source_handle_rejected(registry):
    with pytest.raises(WorkflowError, match="unknown output handle 'sideways'"):
        await execute_workflow(
            wf(
                [
                    trigger(),
                    {"id": "vars", "type": "set_variable", "config": {"variables": "{}"}},
                ],
                [{"source": "start", "target": "vars", "sourceHandle": "sideways"}],
            ),
            registry,
        )


async def test_unknown_target_handle_rejected(registry):
    with pytest.raises(WorkflowError, match="unknown input handle 'side_door'"):
        await execute_workflow(
            wf(
                [
                    trigger(),
                    {"id": "vars", "type": "set_variable", "config": {"variables": "{}"}},
                ],
                [{"source": "start", "target": "vars", "targetHandle": "side_door"}],
            ),
            registry,
        )


async def test_self_connection_rejected(registry):
    with pytest.raises(WorkflowError, match="cycle"):
        await execute_workflow(
            wf(
                [
                    trigger(),
                    {"id": "vars", "type": "set_variable", "config": {"variables": "{}"}},
                ],
                [
                    {"source": "start", "target": "vars"},
                    {"source": "vars", "target": "vars"},
                ],
            ),
            registry,
        )


async def test_duplicate_edges_deduped(registry):
    result = await execute_workflow(
        wf(
            [
                trigger(),
                {"id": "vars", "type": "set_variable", "config": {"variables": '{"a": 1}'}},
            ],
            [
                {"source": "start", "target": "vars", "sourceHandle": "out", "targetHandle": "in"},
                {"source": "start", "target": "vars", "sourceHandle": "out", "targetHandle": "in"},
                {"source": "start", "target": "vars"},  # same edge, handles implicit
            ],
        ),
        registry,
    )
    assert result["status"] == "success"
    assert result["outputs"]["vars"] == {"a": 1}


# ---------- config rules ----------


async def test_missing_required_field_fails_the_node(registry):
    result = await execute_workflow(
        wf(
            [
                trigger(),
                {"id": "req", "type": "http_request", "config": {"method": "GET"}},
            ],
            [{"source": "start", "target": "req"}],
        ),
        registry,
    )
    assert result["node_statuses"]["req"] == "error"
    assert "Missing required field" in result["errors"]["req"]
    assert "URL" in result["errors"]["req"]


async def test_hidden_required_field_not_enforced(registry):
    # llm 'prompt' is required and visible -> counted; http 'body' is not required
    # and hidden for GET. Use if_condition: 'expression' field only matters in
    # expression mode, value fields only in simple mode.
    spec = registry.get("if_condition")
    # simple mode: expression (hidden) missing is fine
    assert (
        missing_required(spec, {"mode": "simple", "value1": "a", "operator": "==", "value2": "a"})
        == []
    )


def test_field_visible_respects_defaults(registry):
    spec = registry.get("if_condition")
    value2 = next(f for f in spec.config_fields if f["key"] == "value2")
    # default mode is 'simple', default operator '==' -> visible without explicit config
    assert field_visible(value2, {}, {"mode": "simple", "operator": "=="})
    # unary operator hides value2
    assert not field_visible(value2, {"operator": "isEmpty"}, {"mode": "simple", "operator": "=="})


def test_missing_required_lists_labels(registry):
    spec = registry.get("write_file")
    missing = missing_required(spec, {"path": "  "})
    assert "Path" in missing
    assert "Content" in missing
