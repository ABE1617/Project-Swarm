import json

from app.engine.types import NodeContext
from app.nodes._google import CREDENTIAL_FIELD, google_api

NODE_TYPE = "docs_create"
NODE_NAME = "Docs: Create Document"
NODE_DESCRIPTION = "Create a Google Doc, optionally with initial content"
NODE_CATEGORY = "Google"
NODE_COLOR = "#4285F4"
NODE_ICON = "docs"
NODE_INPUTS = ["in"]
NODE_OUTPUTS = ["out"]
NODE_TIMEOUT = 90

DOCS = "https://docs.googleapis.com/v1/documents"

CONFIG_FIELDS = [
    CREDENTIAL_FIELD,
    {"key": "title", "label": "Title", "type": "string", "required": True,
     "placeholder": "Notes {{ input.date }}"},
    {"key": "content", "label": "Content", "type": "text",
     "placeholder": "{{ input.text }}", "help": "Optional - inserted as the document body"},
]


async def run(ctx: NodeContext):
    title = str(ctx.config.get("title") or "")
    created = await google_api(ctx, "POST", DOCS, json_body={"title": title})
    document_id = created.get("documentId")

    content = ctx.config.get("content")
    if content not in (None, ""):
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False, indent=2, default=str)
        await google_api(
            ctx,
            "POST",
            f"{DOCS}/{document_id}:batchUpdate",
            json_body={
                "requests": [{"insertText": {"location": {"index": 1}, "text": content}}]
            },
        )

    ctx.log("info", f"Created document '{title}'")
    return {
        "document_id": document_id,
        "title": created.get("title", title),
        "url": f"https://docs.google.com/document/d/{document_id}/edit",
    }
