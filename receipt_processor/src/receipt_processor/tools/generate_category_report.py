from typing import Annotated

from arcade_mcp_server import Context, tool
from arcade_mcp_server.auth import Google

from receipt_processor.models.report_result import ReportResult
from receipt_processor.utils.sheets import (
    PRODUCTS_TAB,
    RECEIPTS_TAB,
    REPORT_HEADERS,
    REPORT_TAB,
    append_rows,
    clear_tab,
    get_all_rows,
    get_or_create_sheet_id,
    replace_pie_chart,
    rows_to_dicts,
)


@tool(requires_auth=Google(scopes=["https://www.googleapis.com/auth/drive.file"]))
async def generate_category_report(
    context: Context,
    spreadsheet_id: Annotated[
        str,
        "Google Spreadsheet ID, discovered by the agent via GoogleSheets.SearchSpreadsheets at session start.",
    ],
) -> ReportResult:
    """Aggregates spending by category across all saved receipts and writes a summary
    to the Report tab with an embedded pie chart.

    Joins the Receipts tab with the Products tab on product_receipt_name to resolve
    categories. Products with no mapping fall under 'Other'. Replaces the Report tab
    contents and any existing chart on each run.
    """
    await context.log.info("Generating category report")
    token = context.get_auth_token_or_empty()

    products = rows_to_dicts(await get_all_rows(token, spreadsheet_id, PRODUCTS_TAB))
    receipts = rows_to_dicts(await get_all_rows(token, spreadsheet_id, RECEIPTS_TAB))
    await context.log.debug(
        f"Loaded {len(products)} products and {len(receipts)} receipts"
    )

    category_map = {
        p["product_receipt_name"]: p["category"]
        for p in products
        if p.get("product_receipt_name") and p.get("category")
    }

    totals: dict[str, float] = {}
    skipped = 0
    for receipt in receipts:
        try:
            total_price = float(receipt["total_price"].replace(",", "."))
        except (KeyError, ValueError):
            skipped += 1
            continue
        category = category_map.get(receipt.get("product_receipt_name", ""), "Other")
        totals[category] = totals.get(category, 0.0) + total_price

    if skipped:
        await context.log.warning(
            f"Skipped {skipped} receipt rows with missing or invalid total_price"
        )

    sorted_totals = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    await context.log.debug(
        f"Aggregated {len(receipts) - skipped} rows into {len(sorted_totals)} categories"
    )

    sheet_id = await get_or_create_sheet_id(token, spreadsheet_id, REPORT_TAB)

    await clear_tab(token, spreadsheet_id, REPORT_TAB)
    rows = [REPORT_HEADERS] + [[cat, round(total, 2)] for cat, total in sorted_totals]
    await append_rows(token, spreadsheet_id, REPORT_TAB, rows)
    await context.log.debug("Written report rows to spreadsheet")

    await replace_pie_chart(token, spreadsheet_id, sheet_id, len(sorted_totals))

    total_spent = round(sum(totals.values()), 2)
    await context.log.info(
        f"Report complete: {len(sorted_totals)} categories, S/ {total_spent} total spent"
    )
    return ReportResult(
        categories=len(sorted_totals),
        total_spent=total_spent,
    )
