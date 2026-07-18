import json
import uuid

from app.engine.types import NodeContext, NodeExecutionError
from app.nodes._google import CREDENTIAL_FIELD, google_api

NODE_TYPE = "drive_upload"
NODE_NAME = "Drive: Upload File"
NODE_DESCRIPTION = "Create a file in Google Drive from workflow data"
NODE_CATEGORY = "Google"
NODE_COLOR = "#F4B400"
NODE_ICON = "drive"
NODE_INPUTS = ["in"]
NODE_OUTPUTS = ["out"]
NODE_TIMEOUT = 120

UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"

CONFIG_FIELDS = [
    CREDENTIAL_FIELD,
    {
        "key": "name",
        "label": "File name",
        "type": "string",
        "required": True,
        "placeholder": "report-{{ input.date }}.txt",
    },
    {
        "key": "content",
        "label": "Content",
        "type": "text",
        "required": True,
        "placeholder": "{{ input.text }}",
    },
    {
        "key": "mime_type",
        "label": "Content type",
        "type": "select",
        "options": ["text/plain", "text/csv", "application/json", "text/html", "text/markdown"],
        "default": "text/plain",
    },
    {
        "key": "folder_id",
        "label": "Folder ID",
        "type": "string",
        "help": "Optional - the ID from the folder's URL; empty uploads to My Drive",
    },
]


async def run(ctx: NodeContext):
    name = str(ctx.config.get("name") or "").strip()
    content = ctx.config.get("content")
    if content is None:
        raise NodeExecutionError("Content is required")
    if not isinstance(content, str):
        content = json.dumps(content, ensure_ascii=False, indent=2, default=str)
    mime_type = str(ctx.config.get("mime_type") or "text/plain")

    metadata: dict = {"name": name, "mimeType": mime_type}
    folder_id = str(ctx.config.get("folder_id") or "").strip()
    if folder_id:
        metadata["parents"] = [folder_id]

    boundary = f"swarm-{uuid.uuid4().hex}"
    body = (
        f"--{boundary}\r\n"
        "Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{json.dumps(metadata)}\r\n"
        f"--{boundary}\r\n"
        f"Content-Type: {mime_type}; charset=UTF-8\r\n\r\n"
        f"{content}\r\n"
        f"--{boundary}--"
    ).encode()

    ctx.log("info", f"Uploading '{name}' ({len(body)} bytes)")
    data = await google_api(
        ctx,
        "POST",
        UPLOAD_URL,
        params={"uploadType": "multipart", "fields": "id,name,mimeType,webViewLink"},
        content=body,
        headers={"Content-Type": f"multipart/related; boundary={boundary}"},
    )
    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "mime_type": data.get("mimeType"),
        "web_view_link": data.get("webViewLink"),
    }
