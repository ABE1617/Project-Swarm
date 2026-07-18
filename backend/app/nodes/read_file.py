import json

from app.engine.types import NodeContext, NodeExecutionError
from app.nodes._files import resolve_sandboxed

NODE_TYPE = "read_file"
NODE_NAME = "Read File"
NODE_DESCRIPTION = "Read a text or JSON file from disk"
NODE_CATEGORY = "Files"
NODE_COLOR = "#8b5cf6"
NODE_ICON = "file-input"
NODE_INPUTS = ["in"]
NODE_OUTPUTS = ["out"]

CONFIG_FIELDS = [
    {
        "key": "path",
        "label": "Path",
        "type": "string",
        "required": True,
        "placeholder": "notes/todo.txt (relative to the data/ sandbox)",
    },
    {
        "key": "format",
        "label": "Format",
        "type": "select",
        "options": ["auto", "text", "json"],
        "default": "auto",
    },
    {"key": "encoding", "label": "Encoding", "type": "string", "default": "utf-8"},
]


async def run(ctx: NodeContext):
    path = resolve_sandboxed(ctx.config.get("path"))
    if not path.exists():
        raise NodeExecutionError(f"File not found: {path}")
    if not path.is_file():
        raise NodeExecutionError(f"Not a file: {path}")

    encoding = ctx.config.get("encoding") or "utf-8"
    try:
        content = path.read_text(encoding=encoding)
    except (UnicodeDecodeError, LookupError) as e:
        raise NodeExecutionError(f"Could not read {path.name} as {encoding}: {e}") from None

    fmt = ctx.config.get("format") or "auto"
    result = {"path": str(path), "size_bytes": path.stat().st_size}

    if fmt == "json" or (fmt == "auto" and path.suffix.lower() == ".json"):
        try:
            result["data"] = json.loads(content)
        except json.JSONDecodeError as e:
            if fmt == "json":
                raise NodeExecutionError(f"{path.name} is not valid JSON: {e}") from None
            result["content"] = content
    else:
        result["content"] = content

    ctx.log("info", f"Read {result['size_bytes']} bytes from {path.name}")
    return result
