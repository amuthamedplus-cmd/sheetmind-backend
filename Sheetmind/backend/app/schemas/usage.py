from datetime import date

from pydantic import BaseModel


class UsageStats(BaseModel):
    period: date
    query_count: int
    formula_count: int
    chat_count: int
    total_used: int
    limit: int
    remaining: int
