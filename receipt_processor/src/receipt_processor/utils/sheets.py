from contextlib import asynccontextmanager
from datetime import datetime, timezone
import httpx

_BASE = "https://sheets.googleapis.com/v4/spreadsheets"

PRODUCTS_TAB = "Products"
PRODUCTS_HEADERS = [
    "product_receipt_name",
    "product_name",
    "source",
    "updated_at",
    "category",
]

CATEGORIES_TAB = "Categories"
CATEGORIES_HEADERS = ["category", "spanish_category"]

REPORT_TAB = "Report"
REPORT_HEADERS = ["category", "total_spent"]

RECEIPTS_TAB = "Receipts"
RECEIPTS_HEADERS = [
    "saved_at",
    "receipt_date",
    "product_receipt_name",
    "product_name",
    "confidence",
    "units",
    "price_per_unit",
    "total_price",
]


def rows_to_dicts(rows: list[list]) -> list[dict]:
    if len(rows) < 2:
        return []
    headers, *data = rows
    return [dict(zip(headers, row)) for row in data]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


@asynccontextmanager
async def _client(token: str):
    async with httpx.AsyncClient(
        timeout=15.0, headers={"Authorization": f"Bearer {token}"}
    ) as client:
        yield client


def _range_url(spreadsheet_id: str, range_: str) -> str:
    return f"{_BASE}/{spreadsheet_id}/values/{range_}"


async def get_categories(token: str, spreadsheet_id: str) -> list[str]:
    await ensure_headers(token, spreadsheet_id, CATEGORIES_TAB, CATEGORIES_HEADERS)
    rows = await get_all_rows(token, spreadsheet_id, CATEGORIES_TAB)
    return [row[0].strip() for row in rows[1:] if row and row[0].strip()]


async def get_all_rows(token: str, spreadsheet_id: str, tab: str) -> list[list]:
    async with _client(token) as client:
        r = await client.get(_range_url(spreadsheet_id, tab))
        r.raise_for_status()
        return r.json().get("values", [])


async def append_rows(
    token: str, spreadsheet_id: str, tab: str, rows: list[list]
) -> None:
    async with _client(token) as client:
        r = await client.post(
            _range_url(spreadsheet_id, f"{tab}!A:Z:append"),
            params={
                "valueInputOption": "USER_ENTERED",
                "insertDataOption": "INSERT_ROWS",
            },
            json={"values": rows},
        )
        r.raise_for_status()


async def update_row(
    token: str, spreadsheet_id: str, tab: str, row: int, values: list, col_end: str
) -> None:
    async with _client(token) as client:
        r = await client.put(
            _range_url(spreadsheet_id, f"{tab}!A{row}:{col_end}{row}"),
            params={"valueInputOption": "USER_ENTERED"},
            json={"values": [values]},
        )
        r.raise_for_status()


async def ensure_headers(
    token: str, spreadsheet_id: str, tab: str, headers: list[str]
) -> None:
    rows = await get_all_rows(token, spreadsheet_id, tab)
    if not rows:
        await append_rows(token, spreadsheet_id, tab, [headers])


async def clear_tab(token: str, spreadsheet_id: str, tab: str) -> None:
    async with _client(token) as client:
        r = await client.post(_range_url(spreadsheet_id, f"{tab}!A:Z:clear"))
        r.raise_for_status()


async def get_or_create_sheet_id(token: str, spreadsheet_id: str, tab_name: str) -> int:
    async with _client(token) as client:
        r = await client.get(
            f"{_BASE}/{spreadsheet_id}",
            params={"fields": "sheets.properties"},
        )
        r.raise_for_status()
        for sheet in r.json().get("sheets", []):
            props = sheet.get("properties", {})
            if props.get("title") == tab_name:
                return props["sheetId"]
        r = await client.post(
            f"{_BASE}/{spreadsheet_id}:batchUpdate",
            json={"requests": [{"addSheet": {"properties": {"title": tab_name}}}]},
        )
        r.raise_for_status()
        return r.json()["replies"][0]["addSheet"]["properties"]["sheetId"]


async def replace_pie_chart(
    token: str, spreadsheet_id: str, sheet_id: int, num_data_rows: int
) -> None:
    async with _client(token) as client:
        r = await client.get(
            f"{_BASE}/{spreadsheet_id}",
            params={"fields": "sheets.charts,sheets.properties.sheetId"},
        )
        r.raise_for_status()
        delete_requests = []
        for sheet in r.json().get("sheets", []):
            if sheet.get("properties", {}).get("sheetId") == sheet_id:
                for chart in sheet.get("charts", []):
                    delete_requests.append(
                        {"deleteEmbeddedObject": {"objectId": chart["chartId"]}}
                    )
        add_request = {
            "addChart": {
                "chart": {
                    "spec": {
                        "title": "Spending by Category",
                        "pieChart": {
                            "legendPosition": "RIGHT_LEGEND",
                            "domain": {
                                "sourceRange": {
                                    "sources": [
                                        {
                                            "sheetId": sheet_id,
                                            "startRowIndex": 1,
                                            "endRowIndex": 1 + num_data_rows,
                                            "startColumnIndex": 0,
                                            "endColumnIndex": 1,
                                        }
                                    ]
                                }
                            },
                            "series": {
                                "sourceRange": {
                                    "sources": [
                                        {
                                            "sheetId": sheet_id,
                                            "startRowIndex": 1,
                                            "endRowIndex": 1 + num_data_rows,
                                            "startColumnIndex": 1,
                                            "endColumnIndex": 2,
                                        }
                                    ]
                                }
                            },
                        },
                    },
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {
                                "sheetId": sheet_id,
                                "rowIndex": 0,
                                "columnIndex": 3,
                            }
                        }
                    },
                }
            }
        }
        r = await client.post(
            f"{_BASE}/{spreadsheet_id}:batchUpdate",
            json={"requests": delete_requests + [add_request]},
        )
        r.raise_for_status()
