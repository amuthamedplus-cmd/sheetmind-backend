from fastapi import APIRouter

from app.core.database import get_supabase

router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "SheetMind API",
        "version": "0.1.0",
    }


@router.get("/health/db")
async def health_check_db():
    """Check Supabase connectivity."""
    try:
        sb = get_supabase()
        result = sb.table("users").select("id").limit(1).execute()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}
