import json

import httpx

from app.engine.types import NodeContext, NodeExecutionError

NODE_TYPE = "http_request"
NODE_NAME = "HTTP Request"
NODE_DESCRIPTION = "Call an API or fetch a URL"
NODE_CATEGORY = "Actions"
NODE_COLOR = "#3b82f6"
NODE_ICON = "globe"
NODE_INPUTS = ["in"]
NODE_OUTPUTS = ["out"]
NODE_TIMEOUT = 150

CONFIG_FIELDS = [
    {"key": "url", "label": "URL", "type": "string", "required": True, "placeholder": "https://api.example.com/items"},
    {"key": "method", "label": "Method", "type": "select", "options": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"], "default": "GET"},
    {"key": "headers", "label": "Headers (JSON)", "type": "json", "placeholder": '{ "Authorization": "Bearer {{ env.MY_API_KEY }}" }'},
    {"key": "params", "label": "Query params (JSON)", "type": "json", "placeholder": '{ "page": 1 }'},
    {"key": "body_type", "label": "Body type", "type": "select", "options": ["none", "json", "text"], "default": "none"},
    {
        "key": "body",
        "label": "Body",
        "type": "text",
        "placeholder": '{ "title": "{{ input.title }}" }',
        "showIf": {"body_type": ["json", "text"]},
    },
    {"key": "timeout", "label": "Timeout (seconds)", "type": "number", "default": 30, "min": 1, "max": 600},
    {"key": "fail_on_error", "label": "Fail on 4xx/5xx response", "type": "boolean", "default": False},
]


def _parse_json_field(value, field_name):
    if value in (None, ""):
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        raise NodeExecutionError(f"{field_name} is not valid JSON: {e}") from None


async def run(ctx: NodeContext):
    url = ctx.config.get("url")
    if not url:
        raise NodeExecutionError("URL is required")
    method = (ctx.config.get("method") or "GET").upper()
    headers = _parse_json_field(ctx.config.get("headers"), "Headers") or {}
    params = _parse_json_field(ctx.config.get("params"), "Query params") or {}
    timeout = min(max(float(ctx.config.get("timeout") or 30), 1), 600)

    body_type = ctx.config.get("body_type") or "none"
    json_body = None
    text_body = None
    if body_type == "json":
        json_body = _parse_json_field(ctx.config.get("body"), "Body")
    elif body_type == "text":
        body_value = ctx.config.get("body")
        text_body = body_value if isinstance(body_value, str) else json.dumps(body_value)

    ctx.log("info", f"{method} {url}")
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            response = await client.request(
                method, url, headers=headers, params=params, json=json_body, content=text_body
            )
    except httpx.TimeoutException:
        raise NodeExecutionError(f"Request to {url} timed out after {timeout:.0f}s") from None
    except httpx.HTTPError as e:
        raise NodeExecutionError(f"Request failed: {e}") from None

    try:
        body = response.json()
    except ValueError:
        body = response.text

    ctx.log("info", f"Response {response.status_code} in {response.elapsed.total_seconds() * 1000:.0f}ms")
    if ctx.config.get("fail_on_error") and response.status_code >= 400:
        raise NodeExecutionError(f"HTTP {response.status_code} from {url}")

    return {
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "body": body,
        "url": str(response.url),
        "elapsed_ms": int(response.elapsed.total_seconds() * 1000),
    }
