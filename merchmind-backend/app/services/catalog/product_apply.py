"""Apply harvested catalog colors onto a Product row after Printify creation."""
import logging

logger = logging.getLogger(__name__)


def apply_catalog_colors(product, product_json: dict, blueprint_id: int, provider_id: int, catalog) -> None:
    library = catalog.ingest_product(blueprint_id, provider_id, product_json)
    if not library:
        product.color_mockups = {}
        return
    product.color_mockups = {v["display_name"]: v.get("front_url", "") for v in library.values()}
    if not product.selected_color:
        with_mockup = next((v["display_name"] for v in library.values() if v.get("front_url")), None)
        product.selected_color = with_mockup or next(iter(library.values()))["display_name"]
    logger.info("catalog.apply product_type=%s colors=%d default=%s",
                getattr(product, "product_type", "?"), len(library), product.selected_color)
