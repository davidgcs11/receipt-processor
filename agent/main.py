import asyncio
import json
import os
from functools import partial
from typing import Any

from agents import Agent, Runner, TResponseInputItem
from agents.exceptions import AgentsException
from agents.run_context import RunContextWrapper
from agents.tool import FunctionTool
from arcadepy import AsyncArcade
from arcadepy.types.execute_tool_response import ExecuteToolResponse
from dotenv import load_dotenv

load_dotenv()

ARCADE_USER_ID = os.getenv("ARCADE_USER_ID")
MCP_SERVERS = ["ReceiptProcessorMcp", "GoogleSearch"]
TOOLS: list[str] = [
    "GoogleSheets_GenerateGoogleFilePickerUrl",
    "GoogleSheets_GetSpreadsheet",
    "GoogleSheets_GetSpreadsheetMetadata",
    "GoogleSheets_SearchSpreadsheets",
    "GoogleSheets_UpdateCells",
    "GoogleSheets_WriteToCell",
]
MODEL = "gpt-5.4-mini"

SYSTEM_PROMPT = """You are a receipt processing assistant for Peruvian Tottus supermarket receipts. Always communicate with the user in English. The receipt data (product names, categories, etc.) is in Spanish — preserve it as-is, do not translate it, but your own messages and questions must always be in English.

Whenever you need clarification, a choice, or any input from the user, call the ask_user tool and wait for the response before continuing. Do not end your turn just to ask a question — use ask_user instead. After ask_user returns a response, you MUST continue executing the next step immediately — never end your turn right after receiving user input.

Follow these steps IN ORDER every time.

**1. Find the target spreadsheet**
Use GoogleSheets.SearchSpreadsheets to find the spreadsheet. Show the results and ask the user which one to use. Remember the spreadsheet_id for all subsequent steps.

**2. Verify the spreadsheet structure**
Use GoogleSheets.GetSpreadsheetMetadata to check if "Products", "Receipts", "Categories", and "Report" tabs exist. If any is missing, create the headers now with GoogleSheets.UpdateCells before doing anything else:
- Products (row 1): product_receipt_name | product_name | source | updated_at | category
- Receipts (row 1): saved_at | receipt_date | product_receipt_name | product_name | confidence | units | price_per_unit | total_price
- Categories (row 1): category | spanish_category

**3. Decode the receipt**
Ask the user for the image_url and call decode_receipt.

**4. Load all available categories**
Use GoogleSheets.GetSpreadsheet to read "Categories" tab and have all available categories. Remember categories and use them when processing each product

**5. Process each product**
For each item from decode_receipt, run this flow in order:

  a. Check the Products tab cache with GoogleSheets.GetSpreadsheet (sheet_id_or_name="Products"). If product_receipt_name already exists in column A, use that product_name and category with confidence=100 — skip to the next item.

  b. If not cached, run GoogleSearch.Search with query "{product_receipt_name} site:tottus.com.pe" in lowercase and n_results=2.

  c. Call identify_product with the product_receipt_name, price_per_unit, the search snippets and the categories.

  d. If confidence >= 70: immediately save the product to the Products tab with GoogleSheets.UpdateCells (source="search"). Do not wait until the end.

  e. If confidence < 70: tell the user the product_receipt_name and best candidate name,
         - ask for the correct name, do the same for the category. Then save to the Products tab w
         -ith GoogleSheets.UpdateCells (source="user").  

Show a running summary as each item is processed.

**6. Save the receipt**
Once all items have a product_name and category, call save_receipt with the full enriched list and the receipt date (read from the receipt image if possible).

**7. Generate the category report**
Call generate_category_report with the spreadsheet_id. This aggregates spending by category across all saved receipts, writes a summary to the Report tab, and embeds a pie chart. Show the returned totals (number of categories and total amount spent).

**8. Confirm**
Show a final summary table: item name, identified product, confidence, category, source (cache / search / user). Include the spreadsheet URL."""


class ToolError(AgentsException):
    def __init__(self, result: "ExecuteToolResponse | str"):
        self.result = None
        if isinstance(result, str):
            self.message = result
        else:
            self.message = result.output.error.message
            self.result = result

    def __str__(self) -> str:
        if self.result:
            return f"Tool {self.result.tool_name} failed with error: {self.message}"
        return self.message


def convert_output_to_json(output: Any) -> str:
    if isinstance(output, (dict, list)):
        return json.dumps(output)
    return str(output)


async def authorize_tool(
    client: AsyncArcade, context: RunContextWrapper, tool_name: str
) -> None:
    if not context.context.get("user_id"):
        raise ToolError("No user_id in context — authorization required for tool")

    result = await client.tools.authorize(
        tool_name=tool_name,
        user_id=context.context["user_id"],
    )

    if result.status != "completed":
        print(f"\n{tool_name} requires authorization. Open this URL:\n  {result.url}\n")
        await client.auth.wait_for_completion(result)


async def invoke_arcade_tool(
    context: RunContextWrapper,
    tool_args: str,
    tool_name: str,
    client: AsyncArcade,
) -> str:
    args = json.loads(tool_args)
    await authorize_tool(client, context, tool_name)

    print(f"  -> {tool_name}({json.dumps(args)})")
    result = await client.tools.execute(
        tool_name=tool_name,
        input=args,
        user_id=context.context["user_id"],
    )
    if not result.success:
        raise ToolError(result)

    print(f"  <- {tool_name} OK")
    return convert_output_to_json(result.output.value)


async def ask_user_handler(context: RunContextWrapper, tool_args: str) -> str:
    args = json.loads(tool_args)
    question = args.get("question", "")
    print(f"\nAgent: {question}")
    answer = await asyncio.to_thread(input, "You: ")
    return f"{answer}\n[User has responded. Continue with the next step in the workflow without ending your turn.]"


ASK_USER_TOOL = FunctionTool(
    name="ask_user",
    description="Ask the user a question and wait for their response. Use this whenever you need clarification, a choice, or any input from the user before continuing. After receiving the response, you MUST immediately continue processing — do not end your turn.",
    params_json_schema={
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question to present to the user",
            }
        },
        "required": ["question"],
    },
    on_invoke_tool=ask_user_handler,
    strict_json_schema=False,
)


async def get_arcade_tools(
    client: AsyncArcade,
    tools: list[str],
    mcp_servers: list[str],
) -> list[FunctionTool]:
    tool_formats: list[Any] = []

    if tools:
        print(f"[arcade] Fetching {len(tools)} individual tool(s): {tools}")
        responses = await asyncio.gather(
            *[
                client.tools.formatted.get(name=tool_id, format="openai")
                for tool_id in tools
            ]
        )
        tool_formats.extend(responses)
        print(f"[arcade] Loaded {len(responses)} individual tool(s)")

    if mcp_servers:
        print(
            f"[arcade] Fetching tools from {len(mcp_servers)} MCP server(s): {mcp_servers}"
        )
        responses = await asyncio.gather(
            *[
                client.tools.formatted.list(toolkit=tk, format="openai")
                for tk in mcp_servers
            ]
        )
        for tk, response in zip(mcp_servers, responses):
            names = [t["function"]["name"] for t in response.items]
            print(
                f"[arcade]   {tk}: {len(names)} tool(s) loaded — {names if names else '(none)'}"
            )
            tool_formats.extend(response.items)

    result = []
    for tool in tool_formats:
        name = tool["function"]["name"]
        result.append(
            FunctionTool(
                name=name,
                description=tool["function"]["description"],
                params_json_schema=tool["function"]["parameters"],
                on_invoke_tool=partial(
                    invoke_arcade_tool, tool_name=name, client=client
                ),
                strict_json_schema=False,
            )
        )

    print(f"[arcade] Total tools registered: {len(result)}")
    return result


async def main() -> None:
    client = AsyncArcade()

    tools = await get_arcade_tools(client, tools=TOOLS, mcp_servers=MCP_SERVERS)
    tools.append(ASK_USER_TOOL)
    agent = Agent(
        name="Receipt Processor",
        instructions=SYSTEM_PROMPT,
        model=MODEL,
        tools=tools,
    )

    history: list[TResponseInputItem] = []
    print("Receipt Processor Agent (type 'exit' to quit)")
    print("-" * 50)

    while True:
        prompt = input("You: ").strip()
        if prompt.lower() == "exit":
            break

        history.append({"role": "user", "content": prompt})
        try:
            result = await Runner.run(
                starting_agent=agent,
                input=history,
                context={"user_id": ARCADE_USER_ID},
                max_turns=50,
            )
            history = result.to_input_list()
            print(f"Assistant: {result.final_output}\n")
        except ToolError as e:
            print(f"Error: {e}\n")
            break


if __name__ == "__main__":
    asyncio.run(main())
