from app.engine.types import NodeContext, NodeExecutionError
from app.nodes._google import CREDENTIAL_FIELD, google_api

NODE_TYPE = "calendar_create_event"
NODE_NAME = "Calendar: Create Event"
NODE_DESCRIPTION = "Create an event in Google Calendar"
NODE_CATEGORY = "Google"
NODE_COLOR = "#4285F4"
NODE_ICON = "calendar-g"
NODE_INPUTS = ["in"]
NODE_OUTPUTS = ["out"]
NODE_TIMEOUT = 90

CALENDAR = "https://www.googleapis.com/calendar/v3"

CONFIG_FIELDS = [
    CREDENTIAL_FIELD,
    {"key": "calendar_id", "label": "Calendar", "type": "string", "default": "primary",
     "help": "'primary' or a calendar's ID from its settings"},
    {"key": "title", "label": "Title", "type": "string", "required": True,
     "placeholder": "Sync with {{ input.name }}"},
    {"key": "description", "label": "Description", "type": "text"},
    {"key": "location", "label": "Location", "type": "string"},
    {"key": "all_day", "label": "All-day event", "type": "boolean", "default": False},
    {"key": "start", "label": "Start", "type": "string", "required": True,
     "placeholder": "2026-07-20T15:00:00",
     "help": "ISO date-time; just the date (2026-07-20) for all-day events"},
    {"key": "end", "label": "End", "type": "string", "required": True,
     "placeholder": "2026-07-20T16:00:00"},
    {"key": "timezone", "label": "Time zone", "type": "string", "default": "UTC",
     "showIf": {"all_day": "false"},
     "help": "IANA name, e.g. Europe/Paris"},
    {"key": "attendees", "label": "Attendees", "type": "string",
     "placeholder": "a@example.com, b@example.com"},
]


def _event_time(value: str, all_day: bool, timezone: str) -> dict:
    value = str(value).strip()
    if not value:
        raise NodeExecutionError("Start and End are required")
    if all_day:
        return {"date": value[:10]}
    return {"dateTime": value, "timeZone": timezone}


async def run(ctx: NodeContext):
    all_day = bool(ctx.config.get("all_day", False))
    timezone = str(ctx.config.get("timezone") or "UTC")
    calendar_id = str(ctx.config.get("calendar_id") or "primary")

    body: dict = {
        "summary": str(ctx.config.get("title") or ""),
        "start": _event_time(ctx.config.get("start"), all_day, timezone),
        "end": _event_time(ctx.config.get("end"), all_day, timezone),
    }
    if ctx.config.get("description"):
        body["description"] = str(ctx.config["description"])
    if ctx.config.get("location"):
        body["location"] = str(ctx.config["location"])
    attendees = [
        email.strip()
        for email in str(ctx.config.get("attendees") or "").split(",")
        if email.strip()
    ]
    if attendees:
        body["attendees"] = [{"email": email} for email in attendees]

    ctx.log("info", f"Creating event '{body['summary']}' in {calendar_id}")
    data = await google_api(
        ctx, "POST", f"{CALENDAR}/calendars/{calendar_id}/events", json_body=body
    )
    return {
        "id": data.get("id"),
        "html_link": data.get("htmlLink"),
        "status": data.get("status"),
        "start": data.get("start"),
        "end": data.get("end"),
    }
