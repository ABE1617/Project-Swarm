"""Drop-in node registry tests: user files in nodes/ become palette nodes."""

import textwrap

import pytest

from app import config
from app.engine.executor import execute_workflow
from app.engine.registry import NodeRegistry

VALID_ASYNC_NODE = textwrap.dedent(
    '''
    NODE_TYPE = "shout"
    NODE_NAME = "Shout"
    NODE_DESCRIPTION = "Uppercase a message"
    NODE_CATEGORY = "Data"
    CONFIG_FIELDS = [{"key": "message", "label": "Message", "type": "string"}]

    async def run(ctx):
        return {"shouted": str(ctx.config.get("message", "")).upper()}
    '''
)

VALID_SYNC_NODE = textwrap.dedent(
    '''
    NODE_TYPE = "reverse"
    NODE_NAME = "Reverse"

    def run(ctx):
        return {"reversed": str(ctx.config.get("text", ""))[::-1]}
    '''
)


@pytest.fixture
def nodes_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "NODES_DIR", tmp_path)
    return tmp_path


def test_builtins_load_without_user_dir(nodes_dir):
    registry = NodeRegistry()
    registry.load()
    assert "manual_trigger" in registry.types
    assert "if_condition" in registry.types
    assert registry.get("delay").source == "builtin"
    assert registry.load_errors == []


def test_dropped_file_becomes_node(nodes_dir):
    (nodes_dir / "shout.py").write_text(VALID_ASYNC_NODE)
    registry = NodeRegistry()
    registry.load()
    spec = registry.get("shout")
    assert spec is not None
    assert spec.source == "custom"
    assert spec.name == "Shout"
    assert registry.load_errors == []


async def test_dropped_node_executes_in_workflow(nodes_dir):
    (nodes_dir / "shout.py").write_text(VALID_ASYNC_NODE)
    registry = NodeRegistry()
    registry.load()
    result = await execute_workflow(
        {
            "nodes": [
                {"id": "manual_trigger_1", "type": "manual_trigger", "config": {}},
                {"id": "shout_1", "type": "shout", "config": {"message": "hi"}},
            ],
            "edges": [{"source": "manual_trigger_1", "target": "shout_1"}],
        },
        registry,
    )
    assert result["status"] == "success"
    assert result["outputs"]["shout_1"] == {"shouted": "HI"}


async def test_sync_run_supported(nodes_dir):
    (nodes_dir / "reverse.py").write_text(VALID_SYNC_NODE)
    registry = NodeRegistry()
    registry.load()
    result = await execute_workflow(
        {
            "nodes": [
                {"id": "manual_trigger_1", "type": "manual_trigger", "config": {}},
                {"id": "reverse_1", "type": "reverse", "config": {"text": "abc"}},
            ],
            "edges": [{"source": "manual_trigger_1", "target": "reverse_1"}],
        },
        registry,
    )
    assert result["outputs"]["reverse_1"] == {"reversed": "cba"}


def test_broken_file_reports_error_without_breaking_others(nodes_dir):
    (nodes_dir / "broken.py").write_text("def run(ctx:\n")  # syntax error
    (nodes_dir / "shout.py").write_text(VALID_ASYNC_NODE)
    registry = NodeRegistry()
    registry.load()
    assert registry.get("shout") is not None
    assert any(e["file"] == "broken.py" for e in registry.load_errors)


def test_non_node_file_gets_friendly_error(nodes_dir):
    (nodes_dir / "helpers.py").write_text("x = 1\n")
    registry = NodeRegistry()
    registry.load()
    (entry,) = [e for e in registry.load_errors if e["file"] == "helpers.py"]
    assert "NODE_TYPE" in entry["error"]


def test_underscore_files_ignored(nodes_dir):
    (nodes_dir / "_private.py").write_text("raise RuntimeError('should not be imported')\n")
    registry = NodeRegistry()
    registry.load()
    assert registry.load_errors == []


def test_user_node_overrides_builtin(nodes_dir):
    (nodes_dir / "my_delay.py").write_text(
        textwrap.dedent(
            '''
            NODE_TYPE = "delay"
            NODE_NAME = "My Delay"

            async def run(ctx):
                return {"custom": True}
            '''
        )
    )
    registry = NodeRegistry()
    registry.load()
    spec = registry.get("delay")
    assert spec.source == "custom"
    assert spec.name == "My Delay"


def test_reload_picks_up_new_and_edited_files(nodes_dir):
    registry = NodeRegistry()
    registry.load()
    assert registry.get("shout") is None

    (nodes_dir / "shout.py").write_text(VALID_ASYNC_NODE)
    registry.load()
    assert registry.get("shout") is not None
    assert registry.get("shout").name == "Shout"

    (nodes_dir / "shout.py").write_text(VALID_ASYNC_NODE.replace('"Shout"', '"Shout v2"'))
    registry.load()
    assert registry.get("shout").name == "Shout v2"
