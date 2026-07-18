"""Graph helpers for partial execution."""

from app.engine.types import WorkflowError


def ancestors_subgraph(definition: dict, target: str) -> dict:
    """The sub-workflow containing every node upstream of `target` (excluding it).

    Powers 'Run previous nodes': produces the input data for a node without
    executing the node itself.
    """
    nodes = {n["id"]: n for n in definition.get("nodes", [])}
    if target not in nodes:
        raise WorkflowError(f"Node '{target}' is not in the workflow")

    edges = [
        e
        for e in definition.get("edges", [])
        if e.get("source") in nodes and e.get("target") in nodes
    ]
    incoming: dict[str, list[str]] = {}
    for e in edges:
        incoming.setdefault(e["target"], []).append(e["source"])

    keep: set[str] = set()
    stack = list(incoming.get(target, []))
    while stack:
        nid = stack.pop()
        if nid in keep:
            continue
        keep.add(nid)
        stack.extend(incoming.get(nid, []))

    if not keep:
        raise WorkflowError("This node has no previous nodes to run")

    return {
        "nodes": [n for n in definition["nodes"] if n["id"] in keep],
        "edges": [e for e in edges if e["source"] in keep and e["target"] in keep],
    }
