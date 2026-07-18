import json
import os

import httpx

from app.engine.types import NodeContext, NodeExecutionError

NODE_TYPE = "llm"
NODE_NAME = "LLM"
NODE_DESCRIPTION = (
    "Generate text with OpenAI, DeepSeek, or any OpenAI-compatible API (e.g. local Ollama)"
)
NODE_CATEGORY = "AI"
NODE_COLOR = "#10b981"
NODE_ICON = "sparkles"
NODE_INPUTS = ["in"]
NODE_OUTPUTS = ["out"]
NODE_TIMEOUT = 300

PROVIDERS = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "env_key": "OPENAI_API_KEY",
        "default_model": "gpt-4o-mini",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "env_key": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
    },
    "custom": {"base_url": "", "env_key": "SWARM_LLM_API_KEY", "default_model": ""},
}

CONFIG_FIELDS = [
    {
        "key": "provider",
        "label": "Provider",
        "type": "select",
        "options": ["openai", "deepseek", "custom"],
        "default": "openai",
    },
    {
        "key": "base_url",
        "label": "Base URL",
        "type": "string",
        "placeholder": "http://localhost:11434/v1",
        "help": "Any OpenAI-compatible endpoint (Ollama, LM Studio, vLLM...)",
        "showIf": {"provider": "custom"},
    },
    {
        "key": "model",
        "label": "Model",
        "type": "string",
        "placeholder": "gpt-4o-mini / deepseek-chat / llama3.2",
    },
    {
        "key": "api_key",
        "label": "API key",
        "type": "secret",
        "help": "Leave empty to use the OPENAI_API_KEY / DEEPSEEK_API_KEY env var.",
    },
    {
        "key": "system",
        "label": "System prompt",
        "type": "text",
        "placeholder": "You are a helpful assistant.",
    },
    {
        "key": "prompt",
        "label": "Prompt",
        "type": "text",
        "required": True,
        "placeholder": "Summarize this: {{ input.body }}",
    },
    {
        "key": "temperature",
        "label": "Temperature",
        "type": "number",
        "default": 0.7,
        "min": 0,
        "max": 2,
        "step": 0.1,
    },
    {
        "key": "max_tokens",
        "label": "Max tokens",
        "type": "number",
        "default": 1024,
        "min": 1,
        "max": 128000,
    },
    {"key": "json_mode", "label": "Force JSON output", "type": "boolean", "default": False},
]


async def run(ctx: NodeContext):
    provider_key = ctx.config.get("provider") or "openai"
    provider = PROVIDERS.get(provider_key)
    if provider is None:
        raise NodeExecutionError(f"Unknown provider: {provider_key}")

    base_url = (ctx.config.get("base_url") or provider["base_url"]).rstrip("/")
    if not base_url:
        raise NodeExecutionError("Base URL is required for the custom provider")

    model = ctx.config.get("model") or provider["default_model"]
    if not model:
        raise NodeExecutionError("Model is required")

    api_key = ctx.config.get("api_key") or os.environ.get(provider["env_key"], "")
    if not api_key and provider_key != "custom":
        raise NodeExecutionError(
            f"API key required: set it on the node or via the {provider['env_key']} env var"
        )

    prompt = ctx.config.get("prompt")
    if prompt in (None, ""):
        raise NodeExecutionError("Prompt is required")
    if not isinstance(prompt, str):
        prompt = json.dumps(prompt, ensure_ascii=False, default=str)

    messages = []
    system = ctx.config.get("system")
    if system:
        messages.append({"role": "system", "content": str(system)})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": min(max(float(ctx.config.get("temperature") or 0.7), 0), 2),
        "max_tokens": max(int(ctx.config.get("max_tokens") or 1024), 1),
    }
    if ctx.config.get("json_mode"):
        payload["response_format"] = {"type": "json_object"}

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    ctx.log("info", f"Calling {provider_key} model {model}")
    try:
        async with httpx.AsyncClient(timeout=280) as client:
            response = await client.post(
                f"{base_url}/chat/completions", headers=headers, json=payload
            )
    except httpx.TimeoutException:
        raise NodeExecutionError("LLM request timed out") from None
    except httpx.HTTPError as e:
        raise NodeExecutionError(f"LLM request failed: {e}") from None

    if response.status_code != 200:
        detail = response.text[:500]
        raise NodeExecutionError(f"{provider_key} API error {response.status_code}: {detail}")

    data = response.json()
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise NodeExecutionError(f"Unexpected API response shape: {str(data)[:300]}") from None

    result = {"text": text, "model": data.get("model", model), "usage": data.get("usage", {})}
    if ctx.config.get("json_mode"):
        try:
            result["parsed"] = json.loads(text)
        except json.JSONDecodeError:
            ctx.log("warning", "json_mode was on but the response was not valid JSON")
    return result
