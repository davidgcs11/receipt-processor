from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductIdentification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_name: str
    category: str
    confidence: int = Field(ge=0, le=100)

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v) -> int:
        return max(0, min(100, int(v)))
