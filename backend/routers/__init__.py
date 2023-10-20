from fastapi import APIRouter

from ..core.settings import global_settings
from .api import router as api_router
#from .web import router as web_router

router = APIRouter()

base_url = global_settings.base_url
router.include_router(prefix=base_url+"/api", router=api_router, tags=['API'])
#router.include_router(prefix="", router=web_router, tags=['Web'])
