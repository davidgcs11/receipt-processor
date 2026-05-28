# receipt_processor

MCP server for processing Peruvian Tottus supermarket receipts. Extracts line items from receipt images, resolves abbreviated product names to their full commercial names, and generates category spending reports in Google Sheets.

## Tools

### `decode_receipt`

Extracts structured line items from a receipt image.

**Auth:** `OPENAI_API_KEY` secret  
**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `image_url` | `str` | URL of the receipt image |

**Output:** list of `ReceiptLineItem`
| Field | Type | Description |
|-------|------|-------------|
| `product_receipt_name` | `str` | Exact name as printed on the receipt |
| `units` | `float` | Quantity purchased (weight in kg for sold-by-weight items) |
| `price_per_unit` | `float` | Unit price in Peruvian soles (S/) |
| `total_price` | `float` | Total line item price in soles (S/) |

---

### `identify_product`

Resolves an abbreviated receipt product name to its full commercial name and category using GPT-4o-mini and Google Search snippets.

**Auth:** `OPENAI_API_KEY` secret  
**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `product_receipt_name` | `str` | Abbreviated name as printed on the receipt (e.g. `"LT GLORIA ENT 1L"`) |
| `price_per_unit` | `float` | Unit price, used as a disambiguation hint |
| `search_snippets` | `str` | Plain-text results from a prior `GoogleSearch` call (titles + snippets, max ~2000 chars) |
| `categories` | `list[str]` | Valid category names read from the Categories tab at session start |

**Output:** `ProductIdentification`
| Field | Type | Description |
|-------|------|-------------|
| `product_name` | `str` | Full commercial name (e.g. `"Leche Gloria Entera 1L"`) |
| `category` | `str` | One of the provided categories, or `"Other"` |
| `confidence` | `int` | 0–100. ≥90 clearly identified, 65–89 reasonably certain, 30–64 ambiguous, <30 insufficient data |

---

### `generate_category_report`

Aggregates total spending by category across all saved receipts and writes a summary table with an embedded pie chart to the **Report** tab. Joins the **Receipts** tab with the **Products** tab on `product_receipt_name` to resolve categories. Products with no mapping fall under `"Other"`. Replaces the tab contents and any existing chart on each run.

**Auth:** Google OAuth (`drive.file` scope)  
**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `spreadsheet_id` | `str` | Google Spreadsheet ID |

**Output:** `ReportResult`
| Field | Type | Description |
|-------|------|-------------|
| `categories` | `int` | Number of distinct categories written |
| `total_spent` | `float` | Sum of all receipt line item totals in soles (S/) |

## Spreadsheet schema

| Tab | Columns |
|-----|---------|
| **Products** | `product_receipt_name`, `product_name`, `source`, `updated_at`, `category` |
| **Receipts** | `saved_at`, `receipt_date`, `product_receipt_name`, `product_name`, `confidence`, `units`, `price_per_unit`, `total_price` |
| **Categories** | `category`, `spanish_category` |
| **Report** | `category`, `total_spent` |
