from fastapi import APIRouter

from .api import router as api_router
#from .web import router as web_router

router = APIRouter()

router.include_router(prefix="/api", router=api_router, tags=['API'])
#router.include_router(prefix="", router=web_router, tags=['Web'])
