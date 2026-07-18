"""Branch-aware, concurrent workflow executor.

The old engine ran every node in topological order regardless of conditions.
This one routes data along edges: each edge carries the source handle it left
from (e.g. an If node's "true"/"false"), edges on untaken handles are marked
dead, and a node whose incoming edges are all dead is skipped — recursively.
Independent branches execute concurrently.
"""

import asyncio
import json
import time
from collections import deque
from collections.abc import Callable
from typing import Any

from app.engine.fields import missing_required
from app.engine.registry import NodeRegistry
from app.engine.templating import render_config
from app.engine.types import (
    NodeContext,
    NodeExecutionError,
    NodeOutput,
    TemplateError,
    WorkflowError,
)

EmitFn = Callable[[dict], None]

OUTPUT_PREVIEW_LIMIT = 40_000


def preview(data: Any) -> Any:
    """Shrink huge node outputs for events/persistence (full data still flows between nodes)."""
    try:
        text = json.dumps(data, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        text = str(data)
    if len(text) <= OUTPUT_PREVIEW_LIMIT:
        return data
    return {"__truncated__": True, "preview": text[:OUTPUT_PREVIEW_LIMIT]}


class _EdgeState:
    __slots__ = ("data", "edge", "status")

    def __init__(self, edge: dict):
        self.edge = edge
        self.status = "pending"  # pending | active | dead
        self.data: Any = None


def slice_to_node(definition: dict, target: str, include_target: bool = True) -> dict:
    """Reduce a definition to a node's upstream subgraph.

    include_target=True powers 'Execute step' (run the node with real data);
    include_target=False powers 'Execute previous nodes' (populate input data
    without running the selected node - the n8n input-panel behavior).
    """
    nodes = definition.get("nodes", [])
    if target not in {n.get("id") for n in nodes}:
        raise WorkflowError(f"Node '{target}' is not part of the workflow")
    edges = definition.get("edges", [])

    parents: dict[str, list[str]] = {}
    for e in edges:
        parents.setdefault(e.get("target"), []).append(e.get("source"))

    keep: set[str] = set()
    stack = [target]
    while stack:
        nid = stack.pop()
        if nid in keep:
            continue
        keep.add(nid)
        stack.extend(parents.get(nid, []))

    if not include_target:
        keep.discard(target)
        if not keep:
            raise WorkflowError("This node has no previous nodes to execute")

    return {
        **definition,
        "nodes": [n for n in nodes if n.get("id") in keep],
        "edges": [e for e in edges if e.get("source") in keep and e.get("target") in keep],
    }


def _detect_cycle(nodes: dict, adj: dict[str, list[str]]) -> None:
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {nid: WHITE for nid in nodes}
    for start in nodes:
        if color[start] != WHITE:
            continue
        stack: list[tuple[str, int]] = [(start, 0)]
        color[start] = GRAY
        while stack:
            nid, idx = stack[-1]
            neighbors = adj.get(nid, [])
            if idx < len(neighbors):
                stack[-1] = (nid, idx + 1)
                nxt = neighbors[idx]
                if color[nxt] == GRAY:
                    raise WorkflowError(f"Workflow contains a cycle involving node '{nxt}'")
                if color[nxt] == WHITE:
                    color[nxt] = GRAY
                    stack.append((nxt, 0))
            else:
                color[nid] = BLACK
                stack.pop()


async def execute_workflow(
    definition: dict,
    registry: NodeRegistry,
    run_input: Any = None,
    emit: EmitFn | None = None,
    credential_resolver: Callable | None = None,
) -> dict:
    emit = emit or (lambda event: None)
    started = time.time()

    nodes: dict[str, dict] = {}
    for n in definition.get("nodes", []):
        if not n.get("id") or not n.get("type"):
            raise WorkflowError("Every node needs an 'id' and a 'type'")
        nodes[n["id"]] = n
    if not nodes:
        raise WorkflowError("Workflow has no nodes")

    unknown = sorted({n["type"] for n in nodes.values() if registry.get(n["type"]) is None})
    if unknown:
        raise WorkflowError(f"Unknown node types: {', '.join(unknown)}")

    edges = [
        e
        for e in definition.get("edges", [])
        if e.get("source") in nodes and e.get("target") in nodes
    ]

    triggers = [nid for nid, n in nodes.items() if not registry.get(n["type"]).inputs]
    if not triggers:
        raise WorkflowError("Workflow needs a trigger node (e.g. Manual Trigger)")
    if len(triggers) > 1:
        raise WorkflowError(
            f"Only one trigger node is allowed per workflow (found {len(triggers)}: "
            f"{', '.join(sorted(triggers))})"
        )

    # Validate handles against the node specs and drop duplicate edges.
    seen_edges: set[tuple] = set()
    cleaned_edges = []
    for e in edges:
        src_spec = registry.get(nodes[e["source"]]["type"])
        tgt_spec = registry.get(nodes[e["target"]]["type"])
        if not tgt_spec.inputs:
            raise WorkflowError(f"'{e['target']}' is a trigger and cannot receive connections")
        sh = e.get("sourceHandle") or (src_spec.outputs[0] if src_spec.outputs else "out")
        th = e.get("targetHandle") or tgt_spec.inputs[0]
        if src_spec.outputs and sh not in src_spec.outputs:
            raise WorkflowError(
                f"Edge from '{e['source']}' uses unknown output handle '{sh}' "
                f"(available: {', '.join(src_spec.outputs)})"
            )
        if th not in tgt_spec.inputs:
            raise WorkflowError(
                f"Edge into '{e['target']}' uses unknown input handle '{th}' "
                f"(available: {', '.join(tgt_spec.inputs)})"
            )
        key = (e["source"], sh, e["target"], th)
        if key in seen_edges:
            continue
        seen_edges.add(key)
        cleaned_edges.append(e)
    edges = cleaned_edges

    adj: dict[str, list[str]] = {nid: [] for nid in nodes}
    for e in edges:
        adj[e["source"]].append(e["target"])
    _detect_cycle(nodes, adj)

    # Only nodes reachable from a trigger execute; the rest are reported skipped.
    reachable: set[str] = set()
    queue = deque(triggers)
    while queue:
        nid = queue.popleft()
        if nid in reachable:
            continue
        reachable.add(nid)
        queue.extend(adj[nid])

    statuses: dict[str, str] = {nid: "pending" for nid in nodes}
    outputs: dict[str, Any] = {}
    node_errors: dict[str, str] = {}
    logs: list[dict] = []

    in_edges: dict[str, list[_EdgeState]] = {nid: [] for nid in reachable}
    out_edges: dict[str, list[_EdgeState]] = {nid: [] for nid in reachable}
    for e in edges:
        if e["source"] in reachable and e["target"] in reachable:
            es = _EdgeState(e)
            in_edges[e["target"]].append(es)
            out_edges[e["source"]].append(es)

    emit({"type": "run_state", "status": "running", "total_nodes": len(reachable)})
    for nid in nodes:
        if nid not in reachable:
            statuses[nid] = "skipped"
            emit(
                {
                    "type": "node_state",
                    "node_id": nid,
                    "status": "skipped",
                    "reason": "Not connected to a trigger",
                }
            )

    ready: deque[str] = deque()
    running: dict[asyncio.Task, str] = {}
    start_times: dict[str, float] = {}

    def default_handle(source_id: str) -> str:
        spec = registry.get(nodes[source_id]["type"])
        return spec.outputs[0] if spec.outputs else "out"

    def check_ready(tid: str) -> None:
        if statuses[tid] != "pending":
            return
        ess = in_edges[tid]
        if any(es.status == "pending" for es in ess):
            return
        if any(es.status == "active" for es in ess):
            statuses[tid] = "queued"
            ready.append(tid)
        else:
            statuses[tid] = "skipped"
            emit(
                {
                    "type": "node_state",
                    "node_id": tid,
                    "status": "skipped",
                    "reason": "No active branch reached this node",
                }
            )
            resolve_out(tid, set(), None)

    def resolve_out(nid: str, active_handles: set[str] | None, data: Any) -> None:
        for es in out_edges[nid]:
            if es.status != "pending":
                continue
            handle = es.edge.get("sourceHandle") or default_handle(nid)
            if active_handles is None or handle in active_handles:
                es.status = "active"
                es.data = data
            else:
                es.status = "dead"
        for es in out_edges[nid]:
            check_ready(es.edge["target"])

    def fail(nid: str, message: str) -> None:
        statuses[nid] = "error"
        node_errors[nid] = message
        elapsed_ms = int((time.time() - start_times.get(nid, time.time())) * 1000)
        emit(
            {
                "type": "node_state",
                "node_id": nid,
                "status": "error",
                "error": message,
                "elapsed_ms": elapsed_ms,
            }
        )
        resolve_out(nid, set(), None)

    def make_log(nid: str):
        def log(level: str, message: str) -> None:
            entry = {"level": level, "node_id": nid, "message": str(message)}
            logs.append(entry)
            emit({"type": "log", **entry})

        return log

    async def run_node(nid: str):
        node = nodes[nid]
        spec = registry.get(node["type"])
        active_inputs = [es.data for es in in_edges[nid] if es.status == "active"]
        if not in_edges[nid] and run_input is not None:
            active_inputs = [run_input]

        missing = missing_required(spec, node.get("config", {}))
        if missing:
            plural = "s" if len(missing) > 1 else ""
            raise NodeExecutionError(f"Missing required field{plural}: {', '.join(missing)}")

        scope: dict[str, Any] = dict(outputs)
        scope["input"] = active_inputs[0] if active_inputs else None

        config = render_config(node.get("config", {}), scope)
        ctx = NodeContext(node_id=nid, config=config, inputs=active_inputs, log=make_log(nid))
        if credential_resolver is not None:
            ctx.get_credential = credential_resolver
        result = await asyncio.wait_for(spec.run(ctx), timeout=spec.timeout)

        if isinstance(result, NodeOutput):
            return result.data, ({result.handle} if result.handle is not None else None)
        return result, None

    for t in triggers:
        statuses[t] = "queued"
        ready.append(t)

    try:
        while ready or running:
            while ready:
                nid = ready.popleft()
                statuses[nid] = "running"
                start_times[nid] = time.time()
                emit({"type": "node_state", "node_id": nid, "status": "running"})
                task = asyncio.create_task(run_node(nid))
                running[task] = nid

            done, _ = await asyncio.wait(running.keys(), return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                nid = running.pop(task)
                spec = registry.get(nodes[nid]["type"])
                try:
                    data, handles = task.result()
                except TimeoutError:
                    fail(nid, f"Node timed out after {spec.timeout:.0f}s")
                    continue
                except (TemplateError, NodeExecutionError) as e:
                    fail(nid, str(e))
                    continue
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    fail(nid, f"{type(e).__name__}: {e}")
                    continue

                outputs[nid] = data
                statuses[nid] = "success"
                emit(
                    {
                        "type": "node_state",
                        "node_id": nid,
                        "status": "success",
                        "output": preview(data),
                        "elapsed_ms": int((time.time() - start_times[nid]) * 1000),
                    }
                )
                resolve_out(nid, handles, data)
    except asyncio.CancelledError:
        for task in running:
            task.cancel()
        raise

    status = "error" if node_errors else "success"
    return {
        "status": status,
        "node_statuses": statuses,
        "outputs": {nid: preview(data) for nid, data in outputs.items()},
        "errors": node_errors,
        "logs": logs,
        "elapsed_ms": int((time.time() - started) * 1000),
    }
