"""Admin sub-routers — combined into a single APIRouter for mounting."""

from fastapi import APIRouter

from app.routers.admin.circulars import router as circulars_router
from app.routers.admin.dashboard import router as dashboard_router
from app.routers.admin.news import router as news_router
from app.routers.admin.prompts import router as prompts_router
from app.routers.admin.review import router as review_router
from app.routers.admin.scraper import router as scraper_router
from app.routers.admin.uploads import router as uploads_router
from app.routers.admin.users import router as users_router

router = APIRouter(tags=["admin"])

router.include_router(dashboard_router, prefix="/dashboard")
router.include_router(review_router, prefix="/review")
router.include_router(prompts_router, prefix="/prompts")
router.include_router(users_router, prefix="/users")
router.include_router(circulars_router, prefix="/circulars")
router.include_router(scraper_router, prefix="/scraper")
router.include_router(news_router, prefix="/news")
router.include_router(uploads_router, prefix="/uploads")
