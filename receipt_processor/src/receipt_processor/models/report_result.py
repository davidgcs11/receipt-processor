from pydantic import BaseModel, Field


class ReportResult(BaseModel):
    categories: int = Field(ge=0)
    total_spent: float = Field(ge=0)
