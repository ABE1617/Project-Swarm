import json

from app.engine.types import NodeContext, NodeExecutionError
from app.nodes._google import CREDENTIAL_FIELD, extract_spreadsheet_id, google_api

NODE_TYPE = "sheets_append"
NODE_NAME = "Sheets: Append Row"
NODE_DESCRIPTION = "Append one or more rows to a Google Sheet"
NODE_CATEGORY = "Google"
NODE_COLOR = "#0F9D58"
NODE_ICON = "sheets"
NODE_INPUTS = ["in"]
NODE_OUTPUTS = ["out"]
NODE_TIMEOUT = 90

SHEETS = "https://sheets.googleapis.com/v4/spreadsheets"

CONFIG_FIELDS = [
    CREDENTIAL_FIELD,
    {"key": "spreadsheet_id", "label": "Spreadsheet", "type": "string", "required": True,
     "placeholder": "ID or full spreadsheet URL"},
    {"key": "sheet_range", "label": "Sheet", "type": "string", "default": "Sheet1",
     "help": "Sheet name (e.g. Sheet1) or A1 range (e.g. Sheet1!A:C)"},
    {"key": "values", "label": "Row values (JSON)", "type": "json", "required": True,
     "placeholder": '["{{ input.name }}", "{{ input.email }}", 42]',
     "help": 'One row ["a", 1], multiple rows [["a"], ["b"]], or an object '
             "(its values become the row)"},
    {"key": "value_input", "label": "Value interpretation", "type": "select",
     "options": ["USER_ENTERED", "RAW"], "default": "USER_ENTERED",
     "help": "USER_ENTERED parses formulas/dates like typing in the UI; RAW stores as-is"},
]


def normalize_rows(raw) -> list[list]:
    if isinstance(raw, str):
        if not raw.strip():
            raise NodeExecutionError("Row values are required")
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as e:
            raise NodeExecutionError(f"Row values is not valid JSON: {e}") from None
    if isinstance(raw, dict):
        return [list(raw.values())]
    if isinstance(raw, list):
        if not raw:
            raise NodeExecutionError("Row values cannot be empty")
        if all(isinstance(item, list) for item in raw):
            return raw
        return [raw]
    return [[raw]]


async def run(ctx: NodeContext):
    spreadsheet_id = extract_spreadsheet_id(ctx.config.get("spreadsheet_id") or "")
    sheet_range = str(ctx.config.get("sheet_range") or "Sheet1")
    rows = normalize_rows(ctx.config.get("values"))
    value_input = ctx.config.get("value_input") or "USER_ENTERED"

    ctx.log("info", f"Appending {len(rows)} row(s) to {sheet_range}")
    data = await google_api(
        ctx,
        "POST",
        f"{SHEETS}/{spreadsheet_id}/values/{sheet_range}:append",
        params={"valueInputOption": value_input, "insertDataOption": "INSERT_ROWS"},
        json_body={"values": rows},
    )
    updates = data.get("updates", {})
    return {
        "spreadsheet_id": spreadsheet_id,
        "updated_range": updates.get("updatedRange"),
        "updated_rows": updates.get("updatedRows", 0),
        "updated_cells": updates.get("updatedCells", 0),
    }
