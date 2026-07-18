import json

from app.engine.types import NodeContext, NodeExecutionError

NODE_TYPE = "transform"
NODE_NAME = "Transform"
NODE_DESCRIPTION = "Reshape data: pick/omit fields, build objects, parse JSON"
NODE_CATEGORY = "Data"
NODE_COLOR = "#06b6d4"
NODE_ICON = "shuffle"
NODE_INPUTS = ["in"]
NODE_OUTPUTS = ["out"]

CONFIG_FIELDS = [
    {
        "key": "mode",
        "label": "Mode",
        "type": "select",
        "options": ["pick", "omit", "template", "expression", "parse_json", "stringify"],
        "default": "pick",
    },
    {
        "key": "keys",
        "label": "Keys (comma-separated)",
        "type": "string",
        "placeholder": "id, name, email",
        "showIf": {"mode": ["pick", "omit"]},
    },
    {
        "key": "template",
        "label": "Output template (JSON)",
        "type": "json",
        "placeholder": '{ "title": "{{ input.name }}", "source": "swarm" }',
        "showIf": {"mode": "template"},
    },
    {
        "key": "expression",
        "label": "Expression",
        "type": "string",
        "placeholder": "{{ len(input['items']) }}",
        "help": "Wrap in {{ }}; the result becomes this node's output.",
        "showIf": {"mode": "expression"},
    },
    {
        "key": "text",
        "label": "Text to parse",
        "type": "string",
        "placeholder": "{{ input.body }} (defaults to the whole input)",
        "showIf": {"mode": "parse_json"},
    },
]


async def run(ctx: NodeContext):
    mode = ctx.config.get("mode") or "pick"

    if mode in ("pick", "omit"):
        if not isinstance(ctx.input, dict):
            raise NodeExecutionError(f"'{mode}' needs a JSON object as input, got {type(ctx.input).__name__}")
        keys = [k.strip() for k in str(ctx.config.get("keys") or "").split(",") if k.strip()]
        if not keys:
            raise NodeExecutionError("Provide at least one key")
        if mode == "pick":
            return {k: ctx.input.get(k) for k in keys}
        return {k: v for k, v in ctx.input.items() if k not in keys}

    if mode == "template":
        raw = ctx.config.get("template")
        if isinstance(raw, (dict, list)):
            return raw
        if not isinstance(raw, str) or not raw.strip():
            raise NodeExecutionError("Output template is required")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise NodeExecutionError(f"Rendered template is not valid JSON: {e}") from None

    if mode == "expression":
        value = ctx.config.get("expression")
        if isinstance(value, str) and "{{" in value:
            raise NodeExecutionError("Expression was not evaluated - check the template syntax")
        if isinstance(value, str) and not value.strip():
            raise NodeExecutionError("Expression is required")
        return value if isinstance(value, (dict, list)) else {"value": value}

    if mode == "parse_json":
        text = ctx.config.get("text")
        if text in (None, ""):
            text = ctx.input
        if isinstance(text, (dict, list)):
            return text  # already parsed
        try:
            return json.loads(str(text))
        except json.JSONDecodeError as e:
            raise NodeExecutionError(f"Input is not valid JSON: {e}") from None

    if mode == "stringify":
        return {"text": json.dumps(ctx.input, ensure_ascii=False, indent=2, default=str)}

    raise NodeExecutionError(f"Unknown mode: {mode}")
