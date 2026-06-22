"""
Celery task for generating designs from Drew's Mind custom ideas.
Runs on the worker process, not inline in the web request.
"""
import logging
from datetime import datetime

from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models.custom_idea import CustomIdea
from app.models.design import Design
from app.models.product import Product
from app.models.settings import AppSettings
from app.services.design.archetype_classifier import classify_archetype, select_image_api
from app.services.design.prompt_builder import build_image_prompt, generate_text_content, get_product_format
from app.services.design.image_generator import generate_image
from app.services.design.quality_scorer import assign_product_bundle, select_primary_product_type, default_primary_product_type
from app.services.design.font_selector import select_font_pair
from app.services.design.text_compositor import composite_text_on_image, should_composite
from app.services.design.shopify_copy_generator import generate_shopify_copy
from app.utils.text import to_title_case
from app.services.pricing.pricing_engine import calculate_price
from app.services.publishing.printify_publisher import get_base_cost, _DUAL_PRINT_SURCHARGE
from app.utils.storage import storage

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.idea_generator.generate_idea_design", bind=True, max_retries=1)
def generate_idea_design(self, idea_id: str):
    db = SessionLocal()
    try:
        idea = db.query(CustomIdea).filter(CustomIdea.id == idea_id).first()
        if not idea:
            logger.error("Idea %s not found", idea_id)
            return

        idea.status = "generating"
        db.commit()

        settings_row = db.query(AppSettings).first()
        base_markup = settings_row.base_markup if settings_row else {}
        floor_prices = settings_row.floor_prices if settings_row else {}
        trend_boost_max = float(settings_row.trend_boost_max) if settings_row else 0.20
        back_logo_enabled = True
        back_logo_url = settings_row.back_logo_url if settings_row else None
        back_logo_products = settings_row.back_logo_products if settings_row else ["tshirt", "hat"]

        forced_archetype = idea.preferences.get("archetype")
        archetype = forced_archetype if forced_archetype in ("text_only", "illustration", "hybrid", "typographic", "text_icon") else classify_archetype(idea.input_text, "custom")
        image_api = select_image_api(archetype)

        design = Design(
            trend_id=None,
            batch_id=None,
            concept_name=to_title_case(idea.input_text[:100]),
            archetype=archetype,
            image_api_used=image_api,
            status="generating",
        )
        db.add(design)
        db.commit()
        db.refresh(design)
        design_id = str(design.id)

        primary_product = default_primary_product_type(archetype)
        fmt = get_product_format(primary_product)
        image_prompt = build_image_prompt(idea.input_text, archetype, "", idea.input_text[:100], product_type=primary_product)
        design.image_prompt = image_prompt
        db.commit()

        processed_url = None
        if image_api and image_prompt:
            try:
                raw_bytes, api_used = generate_image(image_prompt, image_api, aspect_ratio=fmt["aspect_ratio"])
                design.image_api_used = api_used
                raw_path = storage.design_raw_path(design_id)
                storage.upload(raw_path, raw_bytes)
                design.raw_image_url = storage.upload(raw_path, raw_bytes)

                from app.services.design.bg_remover import remove_white_background
                clean_bytes = remove_white_background(raw_bytes)
                proc_path = storage.design_processed_path(design_id)
                processed_url = storage.upload(proc_path, clean_bytes)

                design.processed_image_url = processed_url
                db.commit()
            except Exception as e:
                logger.warning("Image gen failed for idea %s: %s", idea_id, e)
                archetype = "text_only"
                design.archetype = archetype

        text_content = generate_text_content(idea.input_text, archetype, "")
        font_result = select_font_pair(idea.input_text, archetype, "", text_content.get("primary_text", ""))
        design.font_pair = font_result["font_pair"]
        design.font_reasoning = font_result["reasoning"]
        design.design_style = archetype
        design.primary_text = text_content.get("primary_text")
        design.secondary_text = text_content.get("secondary_text")
        design.tagline = text_content.get("tagline")
        design.text_concept_scoring = text_content.get("text_concept_scoring")

        if processed_url and should_composite(archetype):
            try:
                img_bytes = storage.download(storage.design_processed_path(design_id))
                composited = composite_text_on_image(
                    img_bytes,
                    primary_text=text_content.get("primary_text", idea.input_text),
                    secondary_text=text_content.get("secondary_text"),
                    archetype=archetype,
                )
                processed_url = storage.upload(
                    storage.design_processed_path(design_id), composited, "image/png"
                )
                design.processed_image_url = processed_url
                db.commit()
            except Exception as comp_err:
                logger.warning("Text compositing failed for idea %s: %s", idea_id, comp_err)

        light_variant_url = None
        if not processed_url and archetype in ("text_only", "typographic"):
            try:
                from app.services.design.text_preview import generate_text_preview
                preview_bytes = generate_text_preview(
                    primary_text=text_content.get("primary_text", idea.input_text),
                    secondary_text=text_content.get("secondary_text"),
                    font_pair=font_result["font_pair"],
                    dark_mode=True,
                )
                proc_path = storage.design_processed_path(design_id)
                processed_url = storage.upload(proc_path, preview_bytes)
                design.processed_image_url = processed_url
                light_bytes = generate_text_preview(
                    primary_text=text_content.get("primary_text", idea.input_text),
                    secondary_text=text_content.get("secondary_text"),
                    font_pair=font_result["font_pair"],
                    dark_mode=False,
                )
                light_path = storage.design_light_variant_path(design_id)
                light_variant_url = storage.upload(light_path, light_bytes)
            except Exception:
                pass

        design.quality_score = 32
        design.quality_breakdown = {"concept_clarity": 8, "visual_appeal": 8, "merch_suitability": 8, "originality": 8}

        product_types = assign_product_bundle(archetype, design.quality_breakdown)
        primary_result = select_primary_product_type(
            design.concept_name, archetype, product_types, idea.input_text,
        )
        design.primary_product_type = primary_result["primary_product_type"]
        design.primary_product_type_reasoning = primary_result["reasoning"]
        design.classification = "collection" if len(product_types) >= 3 else "design_idea"
        copy = generate_shopify_copy(idea.input_text, idea.input_text, archetype, product_types, "")
        design.shopify_title = copy["shopify_title"]
        design.shopify_description = copy["shopify_description"]
        design.shopify_tags = copy["shopify_tags"]
        db.commit()

        for pt in product_types:
            base_cost = get_base_cost(pt)
            if back_logo_enabled and pt in back_logo_products:
                base_cost += _DUAL_PRINT_SURCHARGE.get(pt, 2.50)
            pricing = calculate_price(pt, base_cost, 50, base_markup, floor_prices, trend_boost_max)
            product = Product(
                design_id=design.id,
                product_type=pt,
                printify_base_cost=pricing["printify_base_cost"],
                base_markup=pricing["base_markup"],
                trend_adjustment=pricing["trend_adjustment"],
                retail_price=pricing["retail_price"],
                floor_price=pricing["floor_price"],
                margin_flag=pricing["margin_flag"],
                publish_status="pending",
            )
            db.add(product)
        db.commit()

        image_url = design.processed_image_url
        if image_url:
            from app.services.publishing.printify_publisher import _get as _get_printify
            from app.services.design.text_preview import _LIGHT_PRODUCT_TYPES
            svc = _get_printify()
            for product in db.query(Product).filter(Product.design_id == design.id).all():
                try:
                    product_label = product.product_type.replace("_", " ").title()
                    product_back_logo = back_logo_url if (back_logo_enabled and product.product_type in back_logo_products) else None
                    use_image = light_variant_url if (light_variant_url and product.product_type in _LIGHT_PRODUCT_TYPES) else image_url
                    printify_id = svc.create_product(
                        product_type=product.product_type,
                        title=f"{design.shopify_title or design.concept_name} — {product_label}",
                        description=design.shopify_description or "",
                        image_url=use_image,
                        retail_price=float(product.retail_price),
                        back_logo_url=product_back_logo,
                        archetype=design.archetype,
                    )
                    product.printify_product_id = printify_id
                    mockups = svc.generate_mockups(printify_id)
                    product.mockup_urls = mockups
                    db.commit()
                except Exception as e:
                    logger.warning("Printify failed for idea %s pt=%s: %s", idea_id, product.product_type, e)

        # Dynamic Mockups for products missing Printify mockups
        if image_url:
            from app.services.design.dynamic_mockups import get_dynamic_mockups_service
            dm = get_dynamic_mockups_service()
            if dm.is_available():
                for product in db.query(Product).filter(Product.design_id == design.id).all():
                    if not product.mockup_urls or not product.mockup_urls.get("front"):
                        url = dm.render_mockup(product.product_type, image_url, design_id)
                        if url:
                            product.mockup_urls = {"front": url}
                            db.commit()

        # Pillow fallback for anything still missing
        if image_url:
            from app.services.design.mockup_generator import generate_mockup
            import httpx as _httpx
            for product in db.query(Product).filter(Product.design_id == design.id).all():
                if not product.mockup_urls or not product.mockup_urls.get("front"):
                    try:
                        img_resp = _httpx.get(image_url, timeout=15)
                        mockup_bytes = generate_mockup(product.product_type, img_resp.content)
                        if mockup_bytes:
                            mockup_path = storage.mockup_path(design_id, product.product_type, "front")
                            mockup_url = storage.upload(mockup_path, mockup_bytes)
                            product.mockup_urls = {"front": mockup_url}
                            db.commit()
                    except Exception as e:
                        logger.warning("Pillow mockup failed for idea %s pt=%s: %s", idea_id[:8], product.product_type, e)

        design.status = "ready"
        idea.design_id = design.id
        idea.status = "complete"
        db.commit()
        logger.info("Idea %s complete: design=%s archetype=%s", idea_id[:8], design_id[:8], archetype)

    except Exception as e:
        logger.error("Idea generation failed for %s: %s", idea_id, e)
        try:
            idea = db.query(CustomIdea).filter(CustomIdea.id == idea_id).first()
            if idea:
                idea.status = "failed"
                db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()
