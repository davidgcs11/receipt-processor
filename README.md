# Arcade Interview

This repo contains two projects that work together to process Peruvian Tottus supermarket receipts using [Arcade](https://arcade.dev) tools.

## Explanation

### Issue + Planning
https://www.loom.com/share/4e3e031a9bac4c40856048c45288adbf

### Demo
https://www.loom.com/share/6d52b80ef31b438094391bafecf2d838

## Projects

### [receipt_processor](./receipt_processor/README.md)

An MCP server (Arcade toolkit) that exposes three tools: decoding receipt images with GPT-4o vision, resolving abbreviated product names to their full commercial names, and generating category spending reports in Google Sheets.

### [agent](./agent/README.md)

An AI agent that orchestrates the receipt_processor tools end-to-end: it takes a receipt image URL, decodes and enriches each line item, writes the data to a Google Spreadsheet, and produces a category spending report with a pie chart.


## Extra
### [files](./files/)

Sample data for testing: five Tottus receipt images (`receipt_1.jpeg` – `receipt_5.jpeg`) and `Expenses.xlsx`, an example of the Google Spreadsheet output with the Products, Receipts, and Categories tabs populated.
