from typing import Annotated, List

from arcade_mcp_server import Context, tool
from openai import AsyncOpenAI
from pydantic import BaseModel

from receipt_processor.models.receipt_line_item import ReceiptLineItem

SYSTEM_PROMPT = """\
You are a data extractor specialized in supermarket receipts.
Extract ALL purchased products from the receipt image.

Rules:
- Include every purchased product, one per item in the list.
- If a field is not legible or missing, use "" for strings and 0 for numbers.
- Prices always as decimal numbers.
- Ignore subtotals, global discounts, taxes, totals, and headers.
- The receipt is in Spanish. Keep product names exactly as they appear — do not translate them."""


class _DecodeReceiptResponse(BaseModel):
    items: List[ReceiptLineItem]


@tool(requires_secrets=["OPENAI_API_KEY"])
async def decode_receipt(
    context: Context, image_url: Annotated[str, "Receipt image url"]
) -> List[ReceiptLineItem]:
    """Extracts structured line items from a supermarket receipt image.

    Accepts a receipt image URL and returns a list of purchased products,
    each with its product receipt name, units, price per unit, and total price.
    """
    api_key = context.get_secret("OPENAI_API_KEY")
    client = AsyncOpenAI(api_key=api_key)

    response = await client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        max_tokens=4096,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            },
        ],
        response_format=_DecodeReceiptResponse,
    )

    return response.choices[0].message.parsed.items
