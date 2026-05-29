# receipt_processor

MCP server for processing Peruvian Tottus supermarket receipts. Extracts line items from receipt images, resolves abbreviated product names, and writes category spending reports to Google Sheets.

## Tools

| Tool | Description |
|------|-------------|
| `decode_receipt` | Takes a receipt image URL and returns structured line items (product name, units, price per unit, total). Uses GPT-4o vision. Requires `OPENAI_API_KEY`. |
| `identify_product` | Resolves an abbreviated receipt name (e.g. `"LT GLORIA ENT 1L"`) to its full commercial name and spending category. Takes the receipt name, unit price, Google Search snippets, and a list of valid categories. Requires `OPENAI_API_KEY`. |
| `generate_category_report` | Reads the Receipts and Products tabs of a Google Spreadsheet, aggregates spending by category, and writes a summary table with a pie chart to the Report tab. Requires Google OAuth (`drive.file` scope). |

## Run locally

**Prerequisites:** Python 3.10+, [uv](https://docs.astral.sh/uv/), an Arcade account.

```bash
# 1. Log in to Arcade
arcade login

# 2. Clone and install
git clone <repo>
cd receipt_processor
uv sync

# 3. Set up environment variables
cp .env.example .env
# Fill in OPENAI_API_KEY and ARCADE_API_KEY in .env

# 4. Start the MCP server
uv run src/receipt_processor/server.py
```

The server will be available locally and registered with your Arcade worker for testing.

## Deploy to Arcade Cloud

```bash
# Publish the toolkit to your Arcade Cloud account
arcade deploy -e src/receipt_processor/server.py
```

After publishing, the tools are available to any agent connected to your Arcade Cloud account. Set the `OPENAI_API_KEY` secret in your Arcade Cloud dashboard under **Secrets**.
