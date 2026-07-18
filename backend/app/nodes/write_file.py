import json

from app.engine.types import NodeContext, NodeExecutionError
from app.nodes._files import resolve_sandboxed

NODE_TYPE = "write_file"
NODE_NAME = "Write File"
NODE_DESCRIPTION = "Write text or JSON to a file on disk"
NODE_CATEGORY = "Files"
NODE_COLOR = "#8b5cf6"
NODE_ICON = "file-output"
NODE_INPUTS = ["in"]
NODE_OUTPUTS = ["out"]

CONFIG_FIELDS = [
    {
        "key": "path",
        "label": "Path",
        "type": "string",
        "required": True,
        "placeholder": "output/result.txt (relative to the data/ sandbox)",
    },
    {
        "key": "content",
        "label": "Content",
        "type": "text",
        "required": True,
        "placeholder": "{{ input.text }}",
    },
    {
        "key": "mode",
        "label": "Mode",
        "type": "select",
        "options": ["overwrite", "append"],
        "default": "overwrite",
    },
    {"key": "encoding", "label": "Encoding", "type": "string", "default": "utf-8"},
]


async def run(ctx: NodeContext):
    path = resolve_sandboxed(ctx.config.get("path"))

    content = ctx.config.get("content")
    if content is None:
        raise NodeExecutionError("Content is required")
    if isinstance(content, (dict, list)):
        content = json.dumps(content, ensure_ascii=False, indent=2, default=str)
    else:
        content = str(content)

    mode = "a" if (ctx.config.get("mode") == "append") else "w"
    encoding = ctx.config.get("encoding") or "utf-8"

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, mode, encoding=encoding, newline="") as f:
        written = f.write(content)

    ctx.log("info", f"Wrote {written} chars to {path}")
    return {
        "path": str(path),
        "chars_written": written,
        "mode": ctx.config.get("mode") or "overwrite",
    }
