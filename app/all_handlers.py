from aiogram import Router
from app.user_handlers import user_router
from app.admin_handlers import admin_router
from app.admin_user_handlers import admin_user_router
from app.admin_complaint_handlers import admin_complaint_router
from app.admin_stats_handlers import admin_stats_router
from app.admin_audit_handlers import admin_audit_router
from app.admin_location_handlers import admin_location_router
from app.complaint_handlers import complaint_router
from app.location_handlers import location_router
from app.me_handlers import me_router
from app.offer_management_handlers import offer_management_router
from app.request_management_handlers import request_management_router
from app.review_handlers import review_router

router = Router()
router.include_router(admin_router)
router.include_router(admin_user_router)
router.include_router(admin_complaint_router)
router.include_router(admin_stats_router)
router.include_router(admin_audit_router)
router.include_router(admin_location_router)
router.include_router(complaint_router)
router.include_router(location_router)
router.include_router(me_router)
router.include_router(offer_management_router)
router.include_router(request_management_router)
router.include_router(review_router)
router.include_router(user_router)
