from arcadepy import BaseModel
from pydantic import ConfigDict, Field, field_validator


class ReceiptLineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_receipt_name: str = Field(
        description='Exact name as printed on the receipt. e.g. "LT GLORIA ENT 1L"'
    )
    units: float = Field(
        ge=0,
        description="Quantity purchased; weight in kg for sold-by-weight items. Always a decimal with period separator.",
    )
    price_per_unit: float = Field(ge=0, description="Unit price in Peruvian soles (S/)")
    total_price: float = Field(
        ge=0, description="Total price for this line item in soles (S/)"
    )

    @field_validator("product_receipt_name", mode="before")
    @classmethod
    def strip_and_validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("product_receipt_name must not be empty")
        return v
