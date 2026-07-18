from app.engine.types import NodeContext
from app.nodes._google import CREDENTIAL_FIELD, extract_spreadsheet_id, google_api

NODE_TYPE = "sheets_read"
NODE_NAME = "Sheets: Read"
NODE_DESCRIPTION = "Read rows from a Google Sheet"
NODE_CATEGORY = "Google"
NODE_COLOR = "#0F9D58"
NODE_ICON = "sheets"
NODE_INPUTS = ["in"]
NODE_OUTPUTS = ["out"]
NODE_TIMEOUT = 90

SHEETS = "https://sheets.googleapis.com/v4/spreadsheets"

CONFIG_FIELDS = [
    CREDENTIAL_FIELD,
    {
        "key": "spreadsheet_id",
        "label": "Spreadsheet",
        "type": "string",
        "required": True,
        "placeholder": "ID or full spreadsheet URL",
    },
    {
        "key": "sheet_range",
        "label": "Sheet or range",
        "type": "string",
        "default": "Sheet1",
        "help": "Sheet name reads everything; A1 notation (Sheet1!A2:C10) reads a slice",
    },
    {
        "key": "as_objects",
        "label": "First row is headers",
        "type": "boolean",
        "default": True,
        "help": "Return rows as objects keyed by the header row",
    },
]


async def run(ctx: NodeContext):
    spreadsheet_id = extract_spreadsheet_id(ctx.config.get("spreadsheet_id") or "")
    sheet_range = str(ctx.config.get("sheet_range") or "Sheet1")

    data = await google_api(ctx, "GET", f"{SHEETS}/{spreadsheet_id}/values/{sheet_range}")
    values = data.get("values", [])

    if ctx.config.get("as_objects", True) and values:
        headers = [str(h) for h in values[0]]
        rows = [
            {headers[i] if i < len(headers) else f"col_{i}": cell for i, cell in enumerate(row)}
            for row in values[1:]
        ]
    else:
        rows = values

    ctx.log("info", f"Read {len(rows)} row(s) from {data.get('range', sheet_range)}")
    return {"rows": rows, "count": len(rows), "range": data.get("range", sheet_range)}
