import json

from app.engine.types import NodeContext, NodeExecutionError

NODE_TYPE = "set_variable"
NODE_NAME = "Set Variables"
NODE_DESCRIPTION = "Set or override fields on the flowing data"
NODE_CATEGORY = "Data"
NODE_COLOR = "#f59e0b"
NODE_ICON = "variable"
NODE_INPUTS = ["in"]
NODE_OUTPUTS = ["out"]

CONFIG_FIELDS = [
    {
        "key": "variables",
        "label": "Variables (JSON object)",
        "type": "json",
        "required": True,
        "placeholder": '{ "greeting": "Hello {{ input.name }}" }',
        "help": "Values support {{ }} templates.",
    },
    {
        "key": "passthrough",
        "label": "Merge into input",
        "type": "boolean",
        "default": True,
        "help": "When on, input fields are kept and variables are merged over them.",
    },
]


async def run(ctx: NodeContext):
    raw = ctx.config.get("variables")
    if isinstance(raw, str):
        if not raw.strip():
            raise NodeExecutionError("Variables JSON is required")
        try:
            variables = json.loads(raw)
        except json.JSONDecodeError as e:
            raise NodeExecutionError(f"Variables is not valid JSON: {e}") from None
    elif isinstance(raw, dict):
        variables = raw
    else:
        raise NodeExecutionError("Variables must be a JSON object")

    if not isinstance(variables, dict):
        raise NodeExecutionError("Variables must be a JSON object, not a list or scalar")

    if ctx.config.get("passthrough", True) and isinstance(ctx.input, dict):
        return {**ctx.input, **variables}
    return variables
