from typing import Annotated

from arcade_mcp_server import Context, tool
from openai import AsyncOpenAI

from receipt_processor.models.product_identification import ProductIdentification

SYSTEM_PROMPT = """\
You are a product identification assistant for Tottus Peru supermarket receipts.
Given a product name as it appears on the receipt (abbreviated, often in caps) and
Google Search snippets, determine the full commercial name of the product.

Respond ONLY with valid JSON (no markdown):
{"product_name": "<full commercial name>", "confidence": <integer 0-100>}

Confidence rules:
- 90-100: product is clearly identified in the search results
- 65-89: product can be inferred with reasonable certainty
- 30-64: results are ambiguous or only partially relevant
- 0-29: insufficient information to identify the product

Product name rules:
- Full, human-readable name. E.g. "Leche Gloria Entera 1L"
- No price, no store name, no abbreviations"""


@tool(requires_secrets=["OPENAI_API_KEY"])
async def identify_product(
    context: Context,
    product_receipt_name: Annotated[
        str, 'Product name as printed on the Tottus receipt. E.g. "LT GLORIA ENT 1L"'
    ],
    price_per_unit: Annotated[
        float, "Product price per unit as printed on the Tottus receipt"
    ],
    search_snippets: Annotated[
        str,
        "Plain text results from a prior GoogleSearch call. Titles and snippets, one result per line. Max ~2000 characters.",
    ],
) -> dict:
    """Identifies the full commercial name of a Tottus receipt product using GPT-4o-mini.

    Takes a receipt product abbreviation and Google Search snippets, and returns
    the resolved commercial product name with a confidence score (0-100).
    """
    api_key = context.get_secret("OPENAI_API_KEY")
    client = AsyncOpenAI(api_key=api_key)

    user_message = (
        f'Receipt product: "{product_receipt_name}" (price per unit: S/ {price_per_unit})\n\n'
        f"Google Search results:\n{search_snippets}"
    )

    try:
        response = await client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format=ProductIdentification,
        )
        result = response.choices[0].message.parsed
        return result.model_dump()
    except Exception:
        return {"product_name": "Desconocido", "confidence": 0}
