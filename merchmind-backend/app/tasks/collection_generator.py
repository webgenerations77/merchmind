"""
Generate coordinated designs for a themed collection.
Uses the collection's style guide to ensure visual cohesion while
producing unique, varied designs within the theme.
"""
import json
import logging
import re
from datetime import datetime

from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models.collection import Collection
from app.models.design import Design
from app.models.product import Product
from app.models.settings import AppSettings
from app.services.design.archetype_classifier import classify_archetype, select_image_api
from app.services.design.prompt_builder import build_image_prompt, generate_text_content
from app.services.design.image_generator import generate_image
from app.services.design.quality_scorer import assign_product_bundle
from app.services.design.font_selector import select_font_pair
from app.services.design.shopify_copy_generator import generate_shopify_copy
from app.services.pricing.pricing_engine import calculate_price
from app.services.publishing.printify_publisher import get_base_cost, _DUAL_PRINT_SURCHARGE
from app.utils.storage import storage
from app.utils.claude_client import claude

logger = logging.getLogger(__name__)


def _generate_collection_concepts(theme: str, description: str, count: int, style_guide: dict) -> list[dict]:
    """Use Claude to generate unique, varied concept names and angles for a collection."""
    mood = style_guide.get("mood", "")
    prompt = (
        f"Collection theme: \"{theme}\"\n"
        f"Description: \"{description or theme}\"\n"
        f"Mood: {mood or 'general'}\n"
        f"Number of designs needed: {count}\n\n"
        f"Generate {count} unique merchandise design concepts for this collection.\n"
        "Each should share the same theme/mood but have a DIFFERENT subject, angle, or visual approach.\n"
        "For example, if the theme is 'Ocean Vibes', concepts might be: a sea turtle, a sunset wave, an anchor with coral, etc.\n\n"
        "Reply with JSON array: [{\"name\": \"short concept name\", \"subject\": \"specific visual subject to illustrate\"}]"
    )
    try:
        text, _ = claude.haiku(
            "collection_concepts",
            [{"role": "user", "content": prompt}],
            max_tokens=300,
        )
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            return json.loads(match.group())[:count]
    except Exception as e:
        logger.warning("Collection concept generation failed: %s", e)
    return [{"name": f"{theme} #{i+1}", "subject": theme} for i in range(count)]


def _build_collection_prompt(base_prompt: str, style_guide: dict, design_index: int, total: int) -> str:
    """Augment a design prompt with collection style constraints."""
    parts = [base_prompt]
    if style_guide.get("palette"):
        colors = ", ".join(style_guide["palette"])
        parts.append(f"Use this color palette: {colors}.")
    if style_guide.get("mood"):
        parts.append(f"Mood/aesthetic: {style_guide['mood']}.")
    if style_guide.get("constraints"):
        parts.append(style_guide["constraints"])
    parts.append(f"This is design {design_index + 1} of {total} in a coordinated collection — visually cohesive but unique.")
    return " ".join(parts)


@celery_app.task(name="app.tasks.collection_generator.generate_collection_task", bind=True, max_retries=1)
def generate_collection_task(self, collection_id: str, count: int):
    db = SessionLocal()
    try:
        collection = db.query(Collection).filter(Collection.id == collection_id).first()
        if not collection:
            logger.error("Collection %s not found", collection_id)
            return

        style_guide = collection.style_guide or {}
        archetype_override = style_guide.get("archetype_override")

        settings_row = db.query(AppSettings).first()
        base_markup = settings_row.base_markup if settings_row else {}
        floor_prices = settings_row.floor_prices if settings_row else {}
        trend_boost_max = float(settings_row.trend_boost_max) if settings_row else 0.20
        back_logo_enabled = True
        back_logo_url = settings_row.back_logo_url if settings_row else None
        back_logo_products = settings_row.back_logo_products if settings_row else ["tshirt", "hat"]

        concepts = _generate_collection_concepts(
            collection.name, collection.description or "", count, style_guide
        )
        logger.info("Collection %s: generated %d unique concepts", collection_id[:8], len(concepts))

        generated = 0
        for i, concept_data in enumerate(concepts):
            try:
                concept_name = concept_data.get("name", f"{collection.name} #{i+1}")
                concept_subject = concept_data.get("subject", concept_name)

                archetype = archetype_override or classify_archetype(concept_subject, "collection")
                image_api = select_image_api(archetype)

                design = Design(
                    trend_id=None,
                    batch_id=None,
                    collection_id=collection.id,
                    concept_name=concept_name,
                    archetype=archetype,
                    image_api_used=image_api,
                    status="generating",
                )
                db.add(design)
                db.commit()
                db.refresh(design)
                design_id = str(design.id)

                base_prompt = build_image_prompt(concept_subject, archetype, "", concept_name)
                image_prompt = _build_collection_prompt(base_prompt, style_guide, i, count)
                design.image_prompt = image_prompt
                db.commit()

                processed_url = None
                if image_api and image_prompt:
                    try:
                        raw_bytes, api_used = generate_image(image_prompt, image_api)
                        design.image_api_used = api_used
                        raw_path = storage.design_raw_path(design_id)
                        storage.upload(raw_path, raw_bytes)
                        design.raw_image_url = storage.upload(raw_path, raw_bytes)

                        # Background removal for clean mockups
                        try:
                            from rembg import remove, new_session
                            session = new_session("u2netp")
                            clean_bytes = remove(raw_bytes, session=session)
                            proc_path = storage.design_processed_path(design_id)
                            processed_url = storage.upload(proc_path, clean_bytes)
                        except Exception as bg_err:
                            logger.warning("Collection bg removal failed design=%s: %s", design_id[:8], bg_err)
                            proc_path = storage.design_processed_path(design_id)
                            processed_url = storage.upload(proc_path, raw_bytes)

                        design.processed_image_url = processed_url
                        db.commit()
                    except Exception as e:
                        logger.warning("Collection image gen failed design=%s: %s", design_id, e)
                        archetype = "text_only"
                        design.archetype = archetype

                text_content = generate_text_content(concept_subject, archetype, "")
                font_result = select_font_pair(concept_subject, archetype, "", text_content.get("primary_text", ""))
                design.font_pair = font_result["font_pair"]
                design.font_reasoning = font_result["reasoning"]
                design.design_style = archetype

                light_variant_url = None
                if not processed_url and archetype in ("text_only", "typographic"):
                    try:
                        from app.services.design.text_preview import generate_text_preview
                        preview_bytes = generate_text_preview(
                            primary_text=text_content.get("primary_text", concept_name),
                            secondary_text=text_content.get("secondary_text"),
                            font_pair=font_result["font_pair"],
                            dark_mode=True,
                        )
                        proc_path = storage.design_processed_path(design_id)
                        processed_url = storage.upload(proc_path, preview_bytes)
                        design.processed_image_url = processed_url
                        light_bytes = generate_text_preview(
                            primary_text=text_content.get("primary_text", concept_name),
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
                copy = generate_shopify_copy(concept_name, collection.name, archetype, product_types, "")
                design.shopify_title = copy["shopify_title"]
                design.shopify_description = copy["shopify_description"]
                design.shopify_tags = copy["shopify_tags"]

                if collection.name:
                    existing_tags = design.shopify_tags or []
                    design.shopify_tags = list(set(existing_tags + [collection.name]))

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

                # Create Printify products + mockups for all product types
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
                                title=f"{design.shopify_title} — {product_label}",
                                description=design.shopify_description or "",
                                image_url=use_image,
                                retail_price=float(product.retail_price),
                                back_logo_url=product_back_logo,
                            )
                            product.printify_product_id = printify_id
                            mockups = svc.generate_mockups(printify_id)
                            product.mockup_urls = mockups
                            db.commit()
                        except Exception as e:
                            logger.warning("Collection Printify failed design=%s pt=%s: %s", design_id[:8], product.product_type, e)

                design.status = "ready"
                db.commit()
                generated += 1
                logger.info("Collection %s: design %d/%d complete (%s) concept='%s'", collection_id[:8], i + 1, count, design_id[:8], concept_name)

            except Exception as e:
                logger.error("Collection %s: design %d failed: %s", collection_id[:8], i + 1, e)
                db.rollback()

        collection.status = "ready"
        collection.updated_at = datetime.utcnow()
        db.commit()
        logger.info("Collection %s complete: %d/%d designs generated", collection_id[:8], generated, count)

    except Exception as e:
        logger.error("Collection generation failed: %s", e)
        try:
            collection = db.query(Collection).filter(Collection.id == collection_id).first()
            if collection:
                collection.status = "draft"
                db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()
