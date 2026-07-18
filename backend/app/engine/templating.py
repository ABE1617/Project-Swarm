"""{{ }} template resolution for node configs.

Supports:
- Simple dotted paths:  {{ node_id.response.items[0].name }}, {{ input.subject }}
- Env vars (allow-listed): {{ env.OPENAI_API_KEY }}
- Expressions via simpleeval: {{ input['count'] + 1 }}  (subscript syntax for dicts)

A string that is exactly one template resolves to the raw typed value;
templates embedded in larger strings are stringified (dicts/lists as JSON).
"""

import json
import os
import re
from typing import Any

from simpleeval import EvalWithCompoundTypes

from app.config import ENV_ALLOWED_PREFIXES, ENV_ALLOWED_SUFFIXES
from app.engine.types import TemplateError

TEMPLATE_RE = re.compile(r"\{\{(.*?)\}\}", re.DOTALL)
SIMPLE_PATH_RE = re.compile(r"^[A-Za-z_]\w*(?:\.\w+|\[\d+\])*$")
SEGMENT_RE = re.compile(r"([A-Za-z_]\w*)|\[(\d+)\]")


def _env_allowed(name: str) -> bool:
    return name.endswith(ENV_ALLOWED_SUFFIXES) or name.startswith(ENV_ALLOWED_PREFIXES)


def _resolve_path(expr: str, scope: dict[str, Any]) -> Any:
    segments: list[str | int] = []
    for key, index in SEGMENT_RE.findall(expr):
        segments.append(int(index) if index else key)

    root = segments[0]
    if root == "env":
        if len(segments) != 2 or not isinstance(segments[1], str):
            raise TemplateError(f"Invalid env reference: {{{{ {expr} }}}}")
        name = segments[1]
        if not _env_allowed(name):
            raise TemplateError(
                f"Env var '{name}' is not templatable "
                "(allowed: *_API_KEY, *_TOKEN, *_SECRET, SWARM_*)"
            )
        value = os.environ.get(name)
        if value is None:
            raise TemplateError(f"Env var '{name}' is not set")
        return value

    if root not in scope:
        known = ", ".join(sorted(k for k in scope if k != "input")) or "none"
        raise TemplateError(
            f"Unknown reference '{root}' in {{{{ {expr} }}}}. "
            f"Available: input, env, and executed nodes ({known})"
        )

    value = scope[root]
    for seg in segments[1:]:
        try:
            if isinstance(seg, int) or isinstance(value, dict):
                value = value[seg]
            else:
                raise KeyError(seg)
        except (KeyError, IndexError, TypeError):
            raise TemplateError(
                f"Path '{expr}' failed at '{seg}' (value there is {type(value).__name__})"
            ) from None
    return value


def resolve_expression(expr: str, scope: dict[str, Any]) -> Any:
    expr = expr.strip()
    if not expr:
        raise TemplateError("Empty template expression")
    if SIMPLE_PATH_RE.match(expr):
        return _resolve_path(expr, scope)
    # Fall back to a sandboxed expression evaluator for arithmetic/comparisons.
    try:
        evaluator = EvalWithCompoundTypes(names=dict(scope))
        return evaluator.eval(expr)
    except TemplateError:
        raise
    except Exception as e:
        raise TemplateError(f"Could not evaluate {{{{ {expr} }}}}: {e}") from None


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def render_string(text: str, scope: dict[str, Any]) -> Any:
    matches = list(TEMPLATE_RE.finditer(text))
    if not matches:
        return text
    # Whole string is a single template -> return the raw typed value.
    if len(matches) == 1 and matches[0].span() == (0, len(text.strip())) and text.strip() == text:
        return resolve_expression(matches[0].group(1), scope)
    if len(matches) == 1 and text.strip() == matches[0].group(0):
        return resolve_expression(matches[0].group(1), scope)
    return TEMPLATE_RE.sub(lambda m: _stringify(resolve_expression(m.group(1), scope)), text)


def render_config(value: Any, scope: dict[str, Any]) -> Any:
    if isinstance(value, str):
        return render_string(value, scope)
    if isinstance(value, dict):
        return {k: render_config(v, scope) for k, v in value.items()}
    if isinstance(value, list):
        return [render_config(item, scope) for item in value]
    return value
