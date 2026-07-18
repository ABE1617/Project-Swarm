"""Engine tests: everything the old engine could not do."""

import asyncio

import pytest

from app.engine.executor import execute_workflow
from app.engine.registry import get_registry
from app.engine.templating import render_config, render_string
from app.engine.types import TemplateError, WorkflowError


@pytest.fixture(scope="module")
def registry():
    return get_registry()


def wf(nodes, edges):
    return {"nodes": nodes, "edges": edges}


def trigger(nid="start", payload=None):
    config = {"payload": payload} if payload else {}
    return {"id": nid, "type": "manual_trigger", "config": config}


# ---------- templating ----------


def test_template_whole_string_returns_raw_value():
    scope = {"n1": {"count": 42, "items": [{"name": "a"}]}}
    assert render_string("{{ n1.count }}", scope) == 42
    assert render_string("{{ n1.items[0].name }}", scope) == "a"


def test_template_embedded_stringifies():
    scope = {"n1": {"count": 42}}
    assert render_string("total: {{ n1.count }}!", scope) == "total: 42!"


def test_template_expression_arithmetic():
    scope = {"input": {"count": 3}}
    assert render_string("{{ input['count'] + 1 }}", scope) == 4


def test_template_unknown_reference_raises():
    with pytest.raises(TemplateError):
        render_string("{{ nope.x }}", {})


def test_template_renders_nested_config():
    scope = {"input": {"name": "swarm"}}
    config = {"a": ["{{ input.name }}"], "b": {"c": "hi {{ input.name }}"}}
    assert render_config(config, scope) == {"a": ["swarm"], "b": {"c": "hi swarm"}}


# ---------- engine: data flow ----------


async def test_data_flows_between_nodes(registry):
    result = await execute_workflow(
        wf(
            [
                trigger(payload='{"name": "world"}'),
                {
                    "id": "vars",
                    "type": "set_variable",
                    "config": {"variables": '{"greeting": "hello {{ input.name }}"}'},
                },
            ],
            [{"source": "start", "target": "vars", "sourceHandle": "out", "targetHandle": "in"}],
        ),
        registry,
    )
    assert result["status"] == "success"
    assert result["outputs"]["vars"]["greeting"] == "hello world"
    # passthrough merged input
    assert result["outputs"]["vars"]["name"] == "world"


async def test_run_input_overrides_sample_payload(registry):
    result = await execute_workflow(
        wf([trigger(payload='{"name": "sample"}')], []),
        registry,
        run_input={"name": "live"},
    )
    assert result["outputs"]["start"] == {"name": "live"}


# ---------- engine: branching (the headline fix) ----------


async def test_true_branch_runs_false_branch_skips(registry):
    result = await execute_workflow(
        wf(
            [
                trigger(payload='{"count": 5}'),
                {
                    "id": "check",
                    "type": "if_condition",
                    "config": {"mode": "simple", "value1": "{{ input.count }}", "operator": ">", "value2": "3"},
                },
                {"id": "yes", "type": "set_variable", "config": {"variables": '{"branch": "true"}'}},
                {"id": "no", "type": "set_variable", "config": {"variables": '{"branch": "false"}'}},
            ],
            [
                {"source": "start", "target": "check", "sourceHandle": "out", "targetHandle": "in"},
                {"source": "check", "target": "yes", "sourceHandle": "true", "targetHandle": "in"},
                {"source": "check", "target": "no", "sourceHandle": "false", "targetHandle": "in"},
            ],
        ),
        registry,
    )
    assert result["status"] == "success"
    assert result["node_statuses"]["yes"] == "success"
    assert result["node_statuses"]["no"] == "skipped"
    assert "no" not in result["outputs"]


async def test_skip_propagates_downstream(registry):
    result = await execute_workflow(
        wf(
            [
                trigger(payload='{"count": 1}'),
                {
                    "id": "check",
                    "type": "if_condition",
                    "config": {"mode": "simple", "value1": "{{ input.count }}", "operator": ">", "value2": "3"},
                },
                {"id": "yes", "type": "set_variable", "config": {"variables": '{"a": 1}'}},
                {"id": "after_yes", "type": "set_variable", "config": {"variables": '{"b": 2}'}},
            ],
            [
                {"source": "start", "target": "check", "sourceHandle": "out", "targetHandle": "in"},
                {"source": "check", "target": "yes", "sourceHandle": "true", "targetHandle": "in"},
                {"source": "yes", "target": "after_yes", "sourceHandle": "out", "targetHandle": "in"},
            ],
        ),
        registry,
    )
    assert result["node_statuses"]["check"] == "success"  # condition false -> took 'false' handle
    assert result["node_statuses"]["yes"] == "skipped"
    assert result["node_statuses"]["after_yes"] == "skipped"


async def test_node_with_two_parents_runs_if_any_active(registry):
    result = await execute_workflow(
        wf(
            [
                trigger(payload='{"count": 5}'),
                {
                    "id": "check",
                    "type": "if_condition",
                    "config": {"mode": "simple", "value1": "{{ input.count }}", "operator": ">", "value2": "3"},
                },
                {"id": "yes", "type": "set_variable", "config": {"variables": '{"from": "yes"}'}},
                {"id": "no", "type": "set_variable", "config": {"variables": '{"from": "no"}'}},
                {"id": "join", "type": "set_variable", "config": {"variables": '{"joined": true}'}},
            ],
            [
                {"source": "start", "target": "check", "sourceHandle": "out", "targetHandle": "in"},
                {"source": "check", "target": "yes", "sourceHandle": "true", "targetHandle": "in"},
                {"source": "check", "target": "no", "sourceHandle": "false", "targetHandle": "in"},
                {"source": "yes", "target": "join", "sourceHandle": "out", "targetHandle": "in"},
                {"source": "no", "target": "join", "sourceHandle": "out", "targetHandle": "in"},
            ],
        ),
        registry,
    )
    assert result["node_statuses"]["join"] == "success"
    assert result["outputs"]["join"]["from"] == "yes"  # merged from the active branch


# ---------- engine: errors, cycles, triggers ----------


async def test_error_marks_node_and_skips_downstream(registry):
    result = await execute_workflow(
        wf(
            [
                trigger(),
                {"id": "bad", "type": "transform", "config": {"mode": "parse_json", "text": "not valid json {"}},
                {"id": "after", "type": "set_variable", "config": {"variables": '{"a": 1}'}},
            ],
            [
                {"source": "start", "target": "bad", "sourceHandle": "out", "targetHandle": "in"},
                {"source": "bad", "target": "after", "sourceHandle": "out", "targetHandle": "in"},
            ],
        ),
        registry,
    )
    assert result["status"] == "error"
    assert result["node_statuses"]["bad"] == "error"
    assert result["node_statuses"]["after"] == "skipped"
    assert "bad" in result["errors"]


async def test_cycle_rejected(registry):
    with pytest.raises(WorkflowError, match="cycle"):
        await execute_workflow(
            wf(
                [
                    trigger(),
                    {"id": "a", "type": "set_variable", "config": {"variables": "{}"}},
                    {"id": "b", "type": "set_variable", "config": {"variables": "{}"}},
                ],
                [
                    {"source": "start", "target": "a"},
                    {"source": "a", "target": "b"},
                    {"source": "b", "target": "a"},
                ],
            ),
            registry,
        )


async def test_no_trigger_rejected(registry):
    with pytest.raises(WorkflowError, match="trigger"):
        await execute_workflow(
            wf([{"id": "a", "type": "set_variable", "config": {"variables": "{}"}}], []),
            registry,
        )


async def test_unconnected_node_skipped_not_executed(registry):
    result = await execute_workflow(
        wf(
            [
                trigger(),
                {"id": "orphan", "type": "set_variable", "config": {"variables": '{"a": 1}'}},
            ],
            [],
        ),
        registry,
    )
    assert result["node_statuses"]["orphan"] == "skipped"
    assert "orphan" not in result["outputs"]


# ---------- engine: parallelism ----------


async def test_parallel_branches_run_concurrently(registry):
    import time

    started = time.time()
    result = await execute_workflow(
        wf(
            [
                trigger(),
                {"id": "d1", "type": "delay", "config": {"seconds": 0.4}},
                {"id": "d2", "type": "delay", "config": {"seconds": 0.4}},
                {"id": "d3", "type": "delay", "config": {"seconds": 0.4}},
            ],
            [
                {"source": "start", "target": "d1"},
                {"source": "start", "target": "d2"},
                {"source": "start", "target": "d3"},
            ],
        ),
        registry,
    )
    elapsed = time.time() - started
    assert result["status"] == "success"
    assert elapsed < 1.0, f"Delays did not run in parallel (took {elapsed:.2f}s)"
