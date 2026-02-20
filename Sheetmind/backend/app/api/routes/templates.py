from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.core.database import get_supabase
from app.core.auth import get_current_user, require_tier

router = APIRouter(prefix="/templates", tags=["Templates"])


class TemplateCreate(BaseModel):
    category: str
    title: str
    prompt: str
    description: str | None = None


class TemplateResponse(BaseModel):
    id: str
    category: str
    title: str
    prompt: str
    description: str | None
    is_default: bool
    created_by: str | None


@router.get("")
async def list_templates(
    category: str | None = None,
    user: dict = Depends(get_current_user),
):
    """
    List templates — default templates + user's custom templates.
    Optionally filter by category.
    """
    sb = get_supabase()

    # Get default templates
    query = sb.table("templates").select("*").eq("is_default", True)
    if category:
        query = query.eq("category", category)
    defaults = query.order("category").order("title").execute()

    # Get user's custom templates
    custom_query = sb.table("templates").select("*") \
        .eq("created_by", user["id"]) \
        .eq("is_default", False)
    if category:
        custom_query = custom_query.eq("category", category)
    customs = custom_query.order("created_at", desc=True).execute()

    return {
        "templates": defaults.data + customs.data,
        "total": len(defaults.data) + len(customs.data),
        "default_count": len(defaults.data),
        "custom_count": len(customs.data),
    }


@router.get("/categories")
async def list_categories(user: dict = Depends(get_current_user)):
    """List all available template categories."""
    sb = get_supabase()
    result = sb.table("templates") \
        .select("category") \
        .eq("is_default", True) \
        .execute()

    categories = sorted(set(row["category"] for row in result.data))
    return {"categories": categories}


@router.post("", response_model=TemplateResponse)
async def create_template(
    request: TemplateCreate,
    user: dict = Depends(require_tier("pro", "team")),
):
    """Create a custom template. Requires Pro or Team tier."""
    sb = get_supabase()

    result = sb.table("templates").insert({
        "category": request.category,
        "title": request.title,
        "prompt": request.prompt,
        "description": request.description,
        "is_default": False,
        "created_by": user["id"],
    }).execute()

    return result.data[0]


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete a custom template. Users can only delete their own."""
    sb = get_supabase()

    # Verify ownership and that it's not a default template
    existing = sb.table("templates") \
        .select("id, is_default, created_by") \
        .eq("id", template_id) \
        .execute()

    if not existing.data:
        raise HTTPException(status_code=404, detail="Template not found")

    template = existing.data[0]

    if template["is_default"]:
        raise HTTPException(status_code=403, detail="Cannot delete default templates")

    if template["created_by"] != user["id"]:
        raise HTTPException(status_code=403, detail="Cannot delete another user's template")

    sb.table("templates").delete().eq("id", template_id).execute()

    return {"status": "deleted"}
