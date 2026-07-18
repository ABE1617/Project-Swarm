from app.engine.types import NodeContext, NodeExecutionError, NodeOutput

NODE_TYPE = "if_condition"
NODE_NAME = "If"
NODE_DESCRIPTION = "Route the flow down the True or False branch"
NODE_CATEGORY = "Logic"
NODE_COLOR = "#a855f7"
NODE_ICON = "git-branch"
NODE_INPUTS = ["in"]
NODE_OUTPUTS = ["true", "false"]

CONFIG_FIELDS = [
    {"key": "mode", "label": "Mode", "type": "select", "options": ["simple", "expression"], "default": "simple"},
    {"key": "value1", "label": "Value 1", "type": "string", "placeholder": "{{ input.status }}", "showIf": {"mode": "simple"}},
    {
        "key": "operator",
        "label": "Operator",
        "type": "select",
        "options": ["==", "!=", ">", "<", ">=", "<=", "contains", "startsWith", "endsWith", "isEmpty", "isNotEmpty"],
        "default": "==",
        "showIf": {"mode": "simple"},
    },
    {
        "key": "value2",
        "label": "Value 2",
        "type": "string",
        "placeholder": "200",
        "showIf": {
            "mode": "simple",
            "operator": ["==", "!=", ">", "<", ">=", "<=", "contains", "startsWith", "endsWith"],
        },
    },
    {
        "key": "expression",
        "label": "Expression",
        "type": "string",
        "placeholder": "{{ input['count'] > 3 }}",
        "help": "Must be wrapped in {{ }} so it is evaluated (e.g. {{ input['a'] == 'x' }})",
        "showIf": {"mode": "expression"},
    },
]


def _coerce(value):
    if not isinstance(value, str):
        return value
    text = value.strip()
    try:
        return float(text) if "." in text else int(text)
    except ValueError:
        pass
    if text.lower() in ("true", "yes"):
        return True
    if text.lower() in ("false", "no"):
        return False
    return value


def _compare(v1, operator, v2) -> bool:
    if operator == "==":
        return v1 == v2
    if operator == "!=":
        return v1 != v2
    if operator in (">", "<", ">=", "<="):
        try:
            if operator == ">":
                return v1 > v2
            if operator == "<":
                return v1 < v2
            if operator == ">=":
                return v1 >= v2
            return v1 <= v2
        except TypeError:
            raise NodeExecutionError(
                f"Cannot compare {type(v1).__name__} {operator} {type(v2).__name__}"
            ) from None
    if operator == "contains":
        if isinstance(v1, (list, dict)):
            return v2 in v1
        return str(v2) in str(v1)
    if operator == "startsWith":
        return str(v1).startswith(str(v2))
    if operator == "endsWith":
        return str(v1).endswith(str(v2))
    if operator == "isEmpty":
        return v1 is None or v1 == "" or (isinstance(v1, (list, dict)) and not v1)
    if operator == "isNotEmpty":
        return not (v1 is None or v1 == "" or (isinstance(v1, (list, dict)) and not v1))
    raise NodeExecutionError(f"Unknown operator: {operator}")


async def run(ctx: NodeContext):
    mode = ctx.config.get("mode") or "simple"

    if mode == "expression":
        # Templates are resolved by the engine before run(); a wrapped {{ expr }}
        # arrives here as its evaluated value. A leftover raw string means the
        # user forgot the braces.
        value = ctx.config.get("expression")
        if isinstance(value, str):
            text = value.strip().lower()
            if text in ("true", "false"):
                result = text == "true"
            else:
                raise NodeExecutionError(
                    "Expression must be wrapped in {{ }} so it gets evaluated, "
                    'e.g. {{ input["count"] > 3 }}'
                )
        else:
            result = bool(value)
    else:
        v1 = _coerce(ctx.config.get("value1"))
        v2 = _coerce(ctx.config.get("value2"))
        operator = ctx.config.get("operator") or "=="
        result = _compare(v1, operator, v2)

    ctx.log("info", f"Condition evaluated to {result} -> taking the '{str(result).lower()}' branch")
    # Pass the input through unchanged on the taken branch.
    return NodeOutput(data=ctx.input, handle="true" if result else "false")
