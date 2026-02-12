import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api_analytics.fastapi import Analytics

from app.core.config import settings
from app.api.router import api_router

# Configure logging to show INFO level
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm up external connections at startup to avoid cold-start latency."""
    # Warm Supabase connection + HTTP pool across key tables
    try:
        from app.core.database import get_supabase
        sb = get_supabase()
        for table in ("users", "conversations", "messages", "usage_records"):
            sb.table(table).select("id").limit(1).execute()
        logger.info("Supabase client warmed up")
    except Exception as e:
        logger.warning(f"Supabase warm-up failed: {e}")

    # Attempt Redis connection (will set cooldown if unavailable)
    try:
        from app.services.cache import _get_redis
        _get_redis()
    except Exception:
        pass

    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered Google Sheets & Excel add-on with confidence scores and source linking",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"https://.*\.googleusercontent\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Analytics — free latency dashboard at https://www.apianalytics.dev
if settings.API_ANALYTICS_KEY:
    app.add_middleware(Analytics, api_key=settings.API_ANALYTICS_KEY)

app.include_router(api_router, prefix=settings.API_PREFIX)
