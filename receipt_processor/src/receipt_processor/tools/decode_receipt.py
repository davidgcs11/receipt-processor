from typing import Annotated, List

from arcade_mcp_server import Context, tool
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict

from receipt_processor.models.receipt_line_item import ReceiptLineItem

SYSTEM_PROMPT = """\
You are a data extractor specialized in Peruvian Tottus supermarket receipts.
The receipt text is in Spanish — preserve product names exactly as printed.
Extract ALL products from the receipt. Respond ONLY with a valid JSON array, no markdown or extra text.

Format for each element:
{
  "product_receipt_name": "<exact product name as it appears on the receipt>",
  "units": <number of units as a decimal number>,
  "price_per_unit": <unit price in soles as a decimal number>,
  "total_price": <total item price in soles as a decimal number>
}

Rules:
- Include ALL products, one per array element.
- If a numeric field is not legible, use 0.
- Ignore subtotals, global discounts, taxes, and totals.
- The product_receipt_name must be exactly as printed. Do not translate, correct, or expand abbreviations.
- Numbers on the receipt may use a period (.) or a comma (,) as the decimal separator. Always output numbers using a period (.) as the decimal separator (e.g. 1.5, not 1,5).
- Do not confuse the thousands separator with the decimal separator (e.g. "1,500" means one thousand five hundred, not one and a half)."""


class _DecodeReceiptResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

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

    await context.log.info(f"Decoding receipt from {image_url}")

    try:
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

        items = response.choices[0].message.parsed.items
        await context.log.info(f"Extracted {len(items)} line items from receipt")
        return items
    except Exception as e:
        await context.log.error(f"Failed to decode receipt: {e}")
        raise
