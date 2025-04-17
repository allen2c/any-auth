import fastapi

from .evaluate import router as evaluate_router

router = fastapi.APIRouter()
router.include_router(evaluate_router)
