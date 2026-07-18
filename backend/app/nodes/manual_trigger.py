import json

from app.engine.types import NodeContext, NodeExecutionError

NODE_TYPE = "manual_trigger"
NODE_NAME = "Manual Trigger"
NODE_DESCRIPTION = "Starts the workflow when you click Run"
NODE_CATEGORY = "Triggers"
NODE_COLOR = "#22c55e"
NODE_ICON = "play"
NODE_INPUTS = []
NODE_OUTPUTS = ["out"]

CONFIG_FIELDS = [
    {
        "key": "payload",
        "label": "Sample payload (JSON)",
        "type": "json",
        "required": False,
        "placeholder": '{ "name": "world" }',
        "help": "Used as the trigger output when no input is passed at run time.",
    },
]


async def run(ctx: NodeContext):
    # Input passed when starting the run wins over the configured sample payload.
    if ctx.input is not None:
        return ctx.input

    payload = ctx.config.get("payload")
    if isinstance(payload, str) and payload.strip():
        try:
            return json.loads(payload)
        except json.JSONDecodeError as e:
            raise NodeExecutionError(f"Sample payload is not valid JSON: {e}") from None
    if isinstance(payload, (dict, list)):
        return payload
    return {}
