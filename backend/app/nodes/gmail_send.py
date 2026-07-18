import base64
from email.mime.text import MIMEText

from app.engine.types import NodeContext, NodeExecutionError
from app.nodes._google import CREDENTIAL_FIELD, google_api

NODE_TYPE = "gmail_send"
NODE_NAME = "Gmail: Send"
NODE_DESCRIPTION = "Send an email from your Gmail account"
NODE_CATEGORY = "Google"
NODE_COLOR = "#EA4335"
NODE_ICON = "gmail"
NODE_INPUTS = ["in"]
NODE_OUTPUTS = ["out"]
NODE_TIMEOUT = 90

CONFIG_FIELDS = [
    CREDENTIAL_FIELD,
    {
        "key": "to",
        "label": "To",
        "type": "string",
        "required": True,
        "placeholder": "someone@example.com, other@example.com",
    },
    {"key": "cc", "label": "Cc", "type": "string"},
    {"key": "bcc", "label": "Bcc", "type": "string"},
    {
        "key": "subject",
        "label": "Subject",
        "type": "string",
        "required": True,
        "placeholder": "Report for {{ input.date }}",
    },
    {
        "key": "body_type",
        "label": "Format",
        "type": "select",
        "options": ["text", "html"],
        "default": "text",
    },
    {
        "key": "body",
        "label": "Body",
        "type": "text",
        "required": True,
        "placeholder": "Hello,\n\n{{ input.summary }}",
    },
]


async def run(ctx: NodeContext):
    to = str(ctx.config.get("to") or "").strip()
    subject = str(ctx.config.get("subject") or "")
    body = ctx.config.get("body")
    if body is None:
        raise NodeExecutionError("Body is required")
    if not isinstance(body, str):
        import json

        body = json.dumps(body, ensure_ascii=False, indent=2, default=str)

    subtype = "html" if ctx.config.get("body_type") == "html" else "plain"
    mime = MIMEText(body, subtype, "utf-8")
    mime["To"] = to
    if ctx.config.get("cc"):
        mime["Cc"] = str(ctx.config["cc"])
    if ctx.config.get("bcc"):
        mime["Bcc"] = str(ctx.config["bcc"])
    mime["Subject"] = subject

    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
    ctx.log("info", f"Sending email to {to}")
    data = await google_api(
        ctx,
        "POST",
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        json_body={"raw": raw},
    )
    return {
        "id": data.get("id"),
        "thread_id": data.get("threadId"),
        "to": to,
        "subject": subject,
    }
