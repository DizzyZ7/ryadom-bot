from aiogram import Router
from app.handlers_fixed import router as user_router
from app.admin_handlers import admin_router
from app.complaint_handlers import complaint_router

router = Router()
router.include_router(admin_router)
router.include_router(complaint_router)
router.include_router(user_router)
