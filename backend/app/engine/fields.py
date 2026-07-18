"""Config-field rules shared by the executor: visibility (showIf) and required checks.

Mirrored by frontend/src/lib/fields.ts — keep the semantics in sync.
"""

from typing import Any

from app.engine.registry import NodeSpec


def _defaults(spec: NodeSpec) -> dict[str, Any]:
    return {f["key"]: f.get("default") for f in spec.config_fields}


def field_visible(field: dict, config: dict, defaults: dict[str, Any]) -> bool:
    show_if = field.get("showIf")
    if not show_if:
        return True
    for key, expected in show_if.items():
        actual = config.get(key)
        if actual in (None, ""):
            actual = defaults.get(key)
        # lowercase both sides so booleans compare consistently with the JS mirror
        actual_str = str(actual).lower()
        if isinstance(expected, list):
            if actual_str not in [str(v).lower() for v in expected]:
                return False
        elif actual_str != str(expected).lower():
            return False
    return True


def missing_required(spec: NodeSpec, config: dict) -> list[str]:
    """Labels of required, currently-visible fields that have no value."""
    defaults = _defaults(spec)
    missing = []
    for field in spec.config_fields:
        if not field.get("required"):
            continue
        if not field_visible(field, config, defaults):
            continue
        value = config.get(field["key"], field.get("default"))
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field.get("label", field["key"]))
    return missing
