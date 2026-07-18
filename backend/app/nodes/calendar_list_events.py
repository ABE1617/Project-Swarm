from datetime import UTC, datetime

from app.engine.types import NodeContext
from app.nodes._google import CREDENTIAL_FIELD, google_api

NODE_TYPE = "calendar_list_events"
NODE_NAME = "Calendar: List Events"
NODE_DESCRIPTION = "List upcoming events from Google Calendar"
NODE_CATEGORY = "Google"
NODE_COLOR = "#4285F4"
NODE_ICON = "calendar-g"
NODE_INPUTS = ["in"]
NODE_OUTPUTS = ["out"]
NODE_TIMEOUT = 90

CALENDAR = "https://www.googleapis.com/calendar/v3"

CONFIG_FIELDS = [
    CREDENTIAL_FIELD,
    {"key": "calendar_id", "label": "Calendar", "type": "string", "default": "primary"},
    {"key": "time_min", "label": "From", "type": "string",
     "placeholder": "2026-07-20T00:00:00Z (empty = now)"},
    {"key": "time_max", "label": "Until", "type": "string",
     "placeholder": "2026-07-27T00:00:00Z (optional)"},
    {"key": "search", "label": "Search text", "type": "string",
     "help": "Free-text match on title, description, attendees"},
    {"key": "max_results", "label": "Max events", "type": "number", "default": 10,
     "min": 1, "max": 100},
]


def _when(value: dict | None) -> str:
    if not value:
        return ""
    return value.get("dateTime") or value.get("date") or ""


async def run(ctx: NodeContext):
    calendar_id = str(ctx.config.get("calendar_id") or "primary")
    time_min = str(ctx.config.get("time_min") or "").strip()
    if not time_min:
        time_min = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    params: dict = {
        "timeMin": time_min,
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": min(max(int(ctx.config.get("max_results") or 10), 1), 100),
    }
    if ctx.config.get("time_max"):
        params["timeMax"] = str(ctx.config["time_max"]).strip()
    if ctx.config.get("search"):
        params["q"] = str(ctx.config["search"])

    data = await google_api(
        ctx, "GET", f"{CALENDAR}/calendars/{calendar_id}/events", params=params
    )
    events = [
        {
            "id": item.get("id"),
            "title": item.get("summary", ""),
            "start": _when(item.get("start")),
            "end": _when(item.get("end")),
            "location": item.get("location", ""),
            "description": item.get("description", ""),
            "attendees": [a.get("email", "") for a in item.get("attendees", [])],
            "html_link": item.get("htmlLink"),
        }
        for item in data.get("items", [])
    ]
    ctx.log("info", f"Found {len(events)} event(s)")
    return {"count": len(events), "events": events}
