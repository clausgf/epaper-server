from typing import Optional
import datetime
import json
from loguru import logger

import uvicorn
from fastapi import APIRouter, Request, Response, status, Header, HTTPException, Path
from fastapi.responses import FileResponse
router = APIRouter()

MINIMUM_WAITING_TIME = 30


# *** Display management *****************************************************

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
        logger.info(f"Display/alias {id} not found - returning 404")
        raise HTTPException(status_code=404, detail="Display/alias not found")

    display_kv = { key: display.__dict__[key] for key in ["id", "aliases", "size", "bits_per_pixel", "update_interval", "client_update_delay", "rotation"]}
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
async def get_display_image(request: Request, id: str, response: Response, if_none_match: Optional[str] = Header(None)):
    # determine rendering with optional alias lookup
    logger.info(f"GET /api/displays/{id}/image with If-None-Match={if_none_match}")
    display = get_display_by_id(request.app.context, id)
    if display is None:
        logger.info(f"Display/alias {id} not found - returning 404")
        raise HTTPException(status_code=404, detail="Display/alias not found")

    # collect new response header fields
    version = await display.get_version()
    next_client_update = await display.get_next_client_update()
    if next_client_update:
        now = datetime.datetime.now(datetime.timezone.utc)
        seconds_till_update = (next_client_update - now).total_seconds()
        max_age = max(MINIMUM_WAITING_TIME, round(seconds_till_update))
    else:
        max_age = MINIMUM_WAITING_TIME
    headers = {
        "ETag": version, 
        "Cache-Control": f"max-age={max_age}"
        # "Content-Disposition": f'inline; filename="{version}.png"'
    }

    # Return 304 if content did not change
    if if_none_match != None and if_none_match == version:
        return Response("", status.HTTP_304_NOT_MODIFIED, headers=headers)

    # return response
    image_buffer = await display.get_image_buffer()
    return Response(content=image_buffer, media_type="image/png", headers=headers)


# *** Device management ******************************************************

async def get_device_ids(redis):
    ids = set()
    async for key in redis.iscan(match="devices:*"):
        key = str(key)
        id = str(key).split(":")[1]
        print(key, " -> ", id)
        ids.add(id)
    return ids

async def get_device_state(redis, id):
    key = f"devices:{id}:state"
    s = await redis.get(key, encoding='utf-8')
    data = json.loads(s) if s else None
    return data

async def set_device_state(redis, id, value):
    # TODO set expiration to 1 day
    key = f"devices:{id}:state"
    #print(f"Redis set {key} -> {value}")
    await redis.set(key, value)


@router.get(
    "/devices",
    summary="Get all device_ids",
    response_description="JSON dictionary containing links to available devices"
)
async def get_devices(request: Request):
    ctx = request.app.context
    ids = await get_device_ids(ctx.redis)
    links = { id: f"/api/devices/{ids}" for id in ids }
    return { "links": links }


@router.get(
    "/devices/{id}",
    summary="Get general info and current data for a device",
    response_description="JSON dictionary containing the desired information."
)
async def get_device(
    request: Request, 
    id: str = Path(..., title="Display_id or alias")
):
    """
    Get the latest info posted by a device.
    """
    ctx = request.app.context
    state = await get_device_state(ctx.redis, id)
    if state is None:
        logger.info(f"Device {id} not found - returning 404")
        raise HTTPException(status_code=404, detail="Device not found")
    return state


@router.post(
    "/devices/{id}",
    summary="Post the state of the give device",
)
async def post_device(request: Request, id: str):
    ctx = request.app.context
    state = await request.body()
    state_dict = json.loads(state)
    state_dict['received_timestamp'] = datetime.datetime.now().isoformat()
    state = json.dumps(state_dict)

    # publish state to REDIS
    await set_device_state(ctx.redis, id, state)

    # TODO publish state to MQTT
    if ctx.mqtt_client and ctx.mqtt_status_topic:
        topic = ctx.mqtt_status_topic.format( id = id )
        logger.info(f"Publishing status for device {id} to topic {topic}")
        ctx.mqtt_client.publish(topic, payload=state, qos=0, retain=False)

    return ""
