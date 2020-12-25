from loguru import logger
from fastapi import APIRouter, Depends

from ..core.utils import get_redis

router = APIRouter()


@router.get("/")
async def root(redis=Depends(get_redis)):
    count = await redis.get('count')
    return {"count": count}
