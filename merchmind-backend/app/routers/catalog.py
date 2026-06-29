"""Read-only Printify catalog endpoints backing the dashboard color picker."""
import logging

from fastapi import APIRouter, Depends, Query

from app.routers.auth import verify_api_key
from app.services.catalog import mockup_service
from app.services.catalog.catalog_service import get_catalog_service

router = APIRouter(prefix="/catalog", tags=["catalog"])
logger = logging.getLogger(__name__)


def _envelope(data=None, error: str | None = None) -> dict:
    return {"success": error is None, "data": data, "error": error}


@router.get("/blueprints")
def list_blueprints(_: str = Depends(verify_api_key)):
    return _envelope(get_catalog_service().get_blueprints())


@router.get("/colors")
def list_colors(blueprint_id: int = Query(...), provider_id: int = Query(...), _: str = Depends(verify_api_key)):
    return _envelope(get_catalog_service().get_colors(blueprint_id, provider_id))


@router.get("/sizes")
def list_sizes(blueprint_id: int = Query(...), provider_id: int = Query(...), _: str = Depends(verify_api_key)):
    return _envelope(get_catalog_service().get_sizes(blueprint_id, provider_id))


@router.get("/mockup")
def get_mockup(
    blueprint_id: int = Query(...),
    provider_id: int = Query(...),
    color: str = Query(...),
    camera: str = Query("front"),
    _: str = Depends(verify_api_key),
):
    svc = get_catalog_service()
    lib = svc._color_library(blueprint_id, provider_id)
    url = mockup_service.get_mockup_url(lib, color)
    from app.services.catalog.colors import normalize_color_name
    entry = lib.get(normalize_color_name(color), {})
    return _envelope({
        "mockup_url": url,
        "color_name": entry.get("display_name", color),
        "hex": entry.get("hex"),
        "is_light": entry.get("is_light"),
    })


@router.post("/refresh")
def refresh_catalog(_: str = Depends(verify_api_key)):
    get_catalog_service().refresh()
    return _envelope({"status": "refreshed"})
