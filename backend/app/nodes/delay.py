import asyncio

from app.engine.types import NodeContext, NodeExecutionError

NODE_TYPE = "delay"
NODE_NAME = "Delay"
NODE_DESCRIPTION = "Wait before continuing (non-blocking)"
NODE_CATEGORY = "Logic"
NODE_COLOR = "#64748b"
NODE_ICON = "timer"
NODE_INPUTS = ["in"]
NODE_OUTPUTS = ["out"]
NODE_TIMEOUT = 330

MAX_SECONDS = 300

CONFIG_FIELDS = [
    {
        "key": "seconds",
        "label": "Seconds",
        "type": "number",
        "default": 1,
        "required": True,
        "min": 0,
        "max": MAX_SECONDS,
    },
]


async def run(ctx: NodeContext):
    try:
        seconds = float(ctx.config.get("seconds") or 0)
    except (TypeError, ValueError):
        raise NodeExecutionError("Seconds must be a number") from None
    if seconds < 0:
        raise NodeExecutionError("Seconds cannot be negative")
    if seconds > MAX_SECONDS:
        raise NodeExecutionError(f"Delay is capped at {MAX_SECONDS}s")

    await asyncio.sleep(seconds)
    ctx.log("info", f"Waited {seconds:g}s")
    return ctx.input if ctx.input is not None else {"waited_seconds": seconds}
