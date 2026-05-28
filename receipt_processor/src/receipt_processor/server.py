#!/usr/bin/env python3
"""receipt_processor MCP server"""

import sys

from arcade_mcp_server import MCPApp

from receipt_processor.tools import (
    decode_receipt,
    generate_category_report,
    identify_product,
)

app = MCPApp(name="receipt_processor_mcp", version="1.0.0", log_level="DEBUG")

app.add_tool(decode_receipt)
app.add_tool(generate_category_report)
app.add_tool(identify_product)

if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    app.run(transport=transport, host="127.0.0.1", port=8000)
