from typing import Optional
import datetime
from loguru import logger

import uvicorn
from fastapi import APIRouter, Request, Response, status, Header, HTTPException, Path
from fastapi.responses import FileResponse
router = APIRouter()

MINIMUM_WAITING_TIME = 30


def get_display_by_id(context, id):
    display = context.displays.get(id, None)
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
    names = list(ctx.displays.keys()) + list(ctx.aliases.keys())
    links = { name: f"/api/displays/{name}" for name in names }
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
    - size, bits per pixel, rotation
    - update cycle (interval, last update),
    - version of the current image and 
    - a link to the current image.
    All this information is related to the current server side image 
    which might or might not be shown on the related display(s) yet.
    """
    display = get_display_by_id(request.app.context, id)
    if display is None:
        logger.info(f"Display/alias {id} not found - returning 404")
        raise HTTPException(status_code=404, detail="Display/alias not found")

    display_kv = { key: display.__dict__[key] for key in ["id", "size", "bits_per_pixel", "update_interval", "client_update_delay", "rotation"]}
    display_kv.update({
        "version": await display.get_version(),
        "last_update": await display.get_last_update(),
        "next_client_update": await display.get_next_client_update()
    })
    display_kv.update({
        "links": {
            "image": f"/api/displays/{id}/image"
        }
    })
    return display_kv


@router.get(
    "/displays/{id}/image",
    summary="Get the current image for a display",
    response_description="PNG image formatted and optimized for the display"
)
async def get_display_image(request: Request, id: str, response: Response, etag: Optional[str] = Header(None)):
    # determine rendering with optional alias lookup
    logger.info(f"GET /api/displays/{id}/image with ETag={etag}")
    display = get_display_by_id(request.app.context, id)
    if display is None:
        logger.info(f"Display/alias {id} not found - returning 404")
        raise HTTPException(status_code=404, detail="Display/alias not found")

    # collect new response header fields
    version = await display.get_version()
    next_client_update = await display.get_next_client_update()
    now = datetime.datetime.now(datetime.timezone.utc)
    seconds_till_update = (next_client_update - now).total_seconds()
    max_age = max(MINIMUM_WAITING_TIME, round(seconds_till_update))
    headers = {
        "ETag": version, 
        "Cache-Control": f"max-age={max_age}"
        # "Content-Disposition": f'inline; filename="{version}.png"'
    }

    # Return 304 if content did not change
    if etag != None and etag == version:
        return Response("", status.HTTP_304_NOT_MODIFIED, headers=headers)

    # return response
    image_buffer = await display.get_image_buffer()
    return Response(content=image_buffer, media_type="image/png", headers=headers)
