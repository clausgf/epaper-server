from typing import Optional
import datetime
import json
from loguru import logger
import os

from ..core.settings import global_settings
from ..core.epaper import Epaper

import uvicorn
from fastapi import APIRouter, Request, Response, status, Header, HTTPException, Path
from fastapi.responses import FileResponse
router = APIRouter()


# *** Display management *****************************************************

def get_display_by_id(context, id: str) -> Optional[Epaper]:
    display = context.epapers.get(id, None)
    if display is None:
        alias_id = context.aliases.get(id, None)
        display = context.displays.get(alias_id, None)
    return display


@router.get(
    "/displays",
    summary="Get all display_ids and aliases",
    response_description="JSON dictionary containing links to available displays"
)
async def get_displays(request: Request):
    ctx = request.app.context
    names = list(ctx.epapers.keys()) + list(ctx.aliases.keys())
    links = { name: request.url_for("get_display", **{"id": name}) for name in names }
    return { "links": links }


@router.get(
    "/displays/{id}",
    summary="Get general info and current data for a display",
    response_description="JSON dictionary containing the desired information."
)
async def get_display(
    request: Request, 
    id: str = Path(..., title="Display_id or alias")
):
    """
    Get info for the given display like
    - aliases
    - size, bits per pixel, rotation
    - update cycle (interval, last update),
    - version of the current image and 
    - a link to the current image.

    All this information is related to the current server side image 
    which might or might not be shown on the related display(s) yet.
    """
    display = get_display_by_id(request.app.context, id)
    if display is None:
        raise HTTPException(status_code=404, detail="Display/alias not found")

    display_kv = display.settings.model_dump(exclude=["widgets", "font"])
    display_kv.update({
        "version": await display.get_version(),
        "last_update": await display.get_last_update(),
        "next_client_update": await display.get_next_client_update_at()
    })
    display_kv.update({
        "links": {
            "image": request.url_for("get_display_image", **{"id": id})
        }
    })
    return display_kv


@router.get(
    "/displays/{id}/image",
    summary="Get the current image for a display",
    response_description="PNG image formatted and optimized for the display"
)
async def get_display_image(request: Request, id: str, response: Response, if_none_match: Optional[str] = Header(None)):
    # determine rendering with optional alias lookup
    logger.info(f"GET /api/displays/{id}/image with If-None-Match={if_none_match}")
    display = get_display_by_id(request.app.context, id)
    if display is None:
        raise HTTPException(status_code=404, detail="Display/alias not found")

    # collect new response header fields
    etag = await display.get_version()
    next_client_update = await display.get_next_client_update_at()
    if next_client_update:
        now = datetime.datetime.now(datetime.timezone.utc)
        seconds_till_update = (next_client_update - now).total_seconds()
        max_age = max(request.app.context.global_settings.minimum_client_update_interval_s, round(seconds_till_update))
    else:
        max_age = request.app.context.global_settings.minimum_client_update_interval_s
    headers = {
        "ETag": etag, 
        "Cache-Control": f"max-age={max_age}"
        # "Content-Disposition": f'inline; filename="{etag}.png"'
    }

    # Return 304 if content did not change
    if if_none_match != None and if_none_match == etag:
        return Response("", status.HTTP_304_NOT_MODIFIED, headers=headers)

    # return response
    image_buffer = await display.get_image_buffer()
    return Response(content=image_buffer, media_type="image/png", headers=headers)

