from fastapi import APIRouter

from app.api.routes import auth, billing, chart, chat, formula, health, usage, templates

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(chart.router)
api_router.include_router(formula.router)
api_router.include_router(usage.router)
api_router.include_router(billing.router)
api_router.include_router(templates.router)
