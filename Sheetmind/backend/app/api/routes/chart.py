import json
import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator

from app.core.auth import get_current_user

logger = logging.getLogger(__name__)
from app.services.chart_generator import generate_chart
from app.services.confidence import calculate_confidence
from app.services.usage import check_and_increment
from app.services.rate_limiter import check_rate_limit
from app.services.cache import get_cached, set_cached

router = APIRouter(prefix="/chat", tags=["Chart"])


class ChartRequest(BaseModel):
    data: dict
    chart_type: str | None = None
    title: str | None = None

    MAX_TITLE_LENGTH: int = 500
    MAX_DATA_BYTES: int = 5_000_000  # 5 MB

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str | None:
        if v and len(v) > cls.MAX_TITLE_LENGTH:
            raise ValueError(f"Chart title too long ({len(v)} chars). Maximum is {cls.MAX_TITLE_LENGTH}.")
        return v

    @field_validator("data")
    @classmethod
    def validate_data_size(cls, v: dict) -> dict:
        try:
            byte_size = len(json.dumps(v))
        except (TypeError, ValueError):
            byte_size = 0
        if byte_size > cls.MAX_DATA_BYTES:
            mb = byte_size / 1_000_000
            raise ValueError(f"Chart data too large ({mb:.1f} MB). Maximum is {cls.MAX_DATA_BYTES // 1_000_000} MB.")
        return v


class ChartResponse(BaseModel):
    chart_config: dict
    chart_type: str
    confidence_score: float | None = None
    confidence_tier: str | None = None


def _check_limits(user: dict):
    """Check rate limit and monthly quota, atomically increment usage."""
    user_id = user["id"]
    tier = user.get("tier", "free")

    rate = check_rate_limit(user_id, tier)
    if not rate["allowed"]:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please slow down.",
            headers={
                "Retry-After": str(rate["retry_after"] or 60),
                "RateLimit-Limit": str(rate["limit"]),
                "RateLimit-Remaining": "0",
            },
        )
    check_and_increment(user_id, tier, "query_count")


@router.post("/chart", response_model=ChartResponse)
async def generate_chart_endpoint(
    request: ChartRequest,
    user: dict = Depends(get_current_user),
):
    """Generate a Chart.js configuration from spreadsheet data."""
    _check_limits(user)
    user_id = user["id"]

    # Build a cache key from the request
    cache_prompt = f"chart:{request.chart_type or 'auto'}:{request.title or ''}"

    cached = get_cached(
        user_id=user_id,
        endpoint="chart",
        prompt=cache_prompt,
        data=request.data,
    )
    if cached:
        return ChartResponse(**cached)

    chart_config = generate_chart(
        data=request.data,
        chart_type=request.chart_type,
        title=request.title,
    )

    chart_type = chart_config.get("type", request.chart_type or "bar")

    conf = calculate_confidence(
        message=cache_prompt,
        response=str(chart_config),
        sheet_data=request.data,
    )

    response_data = {
        "chart_config": chart_config,
        "chart_type": chart_type,
        "confidence_score": conf["score"],
        "confidence_tier": conf["tier"],
    }

    set_cached(
        user_id=user_id,
        endpoint="chart",
        prompt=cache_prompt,
        data=request.data,
        response=response_data,
    )

    return ChartResponse(**response_data)
