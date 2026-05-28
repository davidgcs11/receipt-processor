from typing import Annotated

from arcade_mcp_server import Context, tool
from openai import AsyncOpenAI

from receipt_processor.models.product_identification import ProductIdentification


def _build_system_prompt(categories: list[str]) -> str:
    category_list = "\n".join(f"- {c}" for c in categories)
    return f"""\
You are a product identification assistant for Tottus Peru supermarket receipts.
Given a product name as it appears on the receipt (abbreviated, often in caps) and
Google Search snippets, determine the full commercial name and category of the product.

Respond ONLY with valid JSON (no markdown):
{{"product_name": "<full commercial name>", "category": "<category>", "confidence": <integer 0-100>}}

Confidence rules:
- 90-100: product is clearly identified in the search results
- 65-89: product can be inferred with reasonable certainty
- 30-64: results are ambiguous or only partially relevant
- 0-29: insufficient information to identify the product

Product name rules:
- Must be in Spanish — use the full commercial name as sold in Peru. E.g. "Leche Gloria Entera 1L"
- No price, no store name, no abbreviations
- Never translate any word to English

Category rules:
- Pick exactly one category from the list below
- If none fit, use "Other"
{category_list}"""


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
    categories: Annotated[
        list[str],
        "List of valid product categories read once from the Categories tab of the spreadsheet at session start.",
    ],
) -> dict:
    """Identifies the full commercial name and category of a Tottus receipt product using GPT-4o-mini.

    Takes a receipt product abbreviation, Google Search snippets, and a pre-loaded list of
    categories, and returns the resolved product name, category, and confidence score (0-100).
    """
    await context.log.info(f"Identifying product: {product_receipt_name!r}")

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
                {"role": "system", "content": _build_system_prompt(categories)},
                {"role": "user", "content": user_message},
            ],
            response_format=ProductIdentification,
        )
        result = response.choices[0].message.parsed
        await context.log.info(
            f"Identified {product_receipt_name!r} as {result.product_name!r} "
            f"(category: {result.category}, confidence: {result.confidence})"
        )
        return result.model_dump()
    except Exception as e:
        await context.log.error(
            f"Failed to identify product {product_receipt_name!r}: {e}"
        )
        return {"product_name": "Unknown", "category": "Other", "confidence": 0}
