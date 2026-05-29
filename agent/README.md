# Receipt Processor Agent

An AI agent that processes Peruvian Tottus supermarket receipts. It decodes receipt images, identifies products via web search, and saves the enriched data to Google Sheets with a category spending report.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package manager
- An [Arcade](https://arcade.dev) account and API key
- An OpenAI API key

## Google Sheets setup
1. Create a new spreadsheet in Google Drive, where the data will be read from and write to. It should have 3 sheets:
  - Products
  - Receipts
  - Categories

2. Inside of categories sheet paste the following content
```
category	spanish_category
Meat & Poultry	Carnes y Aves
Processed Meats	Embutidos y Procesados
Fruits & Vegetables	Frutas y Verduras
Frozen Foods	Congelados
Pantry & Dry Goods	Abarrotes
Canned Goods	Conservas
Dairy & Refrigerated	Lácteos y Refrigerados
Beverages	Bebidas
Breakfast & Cereals	Desayuno y Cereales
Pets	Mascotas
Non-Food	No Alimentario
Other	Otro
```


## Setup

**1. Clone the environment file and fill in your credentials:**

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `ARCADE_API_KEY` | Your Arcade API key |
| `ARCADE_USER_ID` | Your email address (used for Arcade tool authorization) |
| `OPENAI_API_KEY` | Your OpenAI API key |

**2. Create the virtual environment and install dependencies:**

```bash
uv sync
```

This creates a `.venv` folder and installs all dependencies from `pyproject.toml`. You only need to run this once (or after dependency changes).

## Run

```bash
uv run main.py
```

`uv run` automatically uses the project's `.venv` — no need to activate it manually.

## What it does

Once running, the agent will:

1. Search for a Google Spreadsheet to write to
2. Ask for a receipt image URL
3. Decode the receipt and identify each product (via Tottus web search)
4. Save products and receipt data to the spreadsheet
5. Generate a category spending report with a pie chart

## Image helpful links

```
https://imgur.com/TpqXOAE
https://imgur.com/eslBdoL
https://imgur.com/rM5MBVN
https://imgur.com/pghKJDt
https://imgur.com/arAK4JK
```