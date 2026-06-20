"""
Drew's Mind — custom idea endpoints.
Submit your own ideas and MerchMind generates designs from them,
bypassing trend scraping and scoring.
"""
import logging
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.custom_idea import CustomIdea
from app.models.trend import Trend
from app.models.batch import Batch
from app.routers.auth import verify_api_key

router = APIRouter(prefix="/ideas", tags=["ideas"])
logger = logging.getLogger(__name__)


def _envelope(data=None, error: str = None) -> dict:
    return {"success": error is None, "data": data, "error": error}


@router.get("")
def list_ideas(db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """List all custom ideas."""
    ideas = db.query(CustomIdea).order_by(CustomIdea.created_at.desc()).limit(50).all()
    return _envelope([{
        "id": str(i.id),
        "input_text": i.input_text,
        "status": i.status,
        "design_id": str(i.design_id) if i.design_id else None,
        "preferences": i.preferences,
        "created_at": i.created_at.isoformat(),
    } for i in ideas])


@router.post("")
def create_idea(body: dict, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """
    Submit a custom idea. MerchMind will generate a design from it.
    Body: {text: "your idea", preferences: {archetype: "illustration", ...}}
    """
    text = body.get("text", "").strip()
    if not text:
        return _envelope(error="Text is required")

    preferences = body.get("preferences", {})

    idea = CustomIdea(
        input_text=text,
        source="drews_mind",
        status="pending",
        preferences=preferences,
    )
    db.add(idea)
    db.commit()
    db.refresh(idea)

    # Generate design inline
    try:
        idea.status = "generating"
        db.commit()

        design_id = _generate_from_idea(idea, db)
        idea.design_id = design_id
        idea.status = "complete"
        db.commit()

        return _envelope({
            "id": str(idea.id),
            "status": "complete",
            "design_id": str(design_id),
            "message": "Design generated from your idea",
        })
    except Exception as e:
        logger.error(f"Custom idea generation failed: {e}")
        idea.status = "failed"
        db.commit()
        return _envelope(error=f"Generation failed: {e}")


def _generate_from_idea(idea: CustomIdea, db: Session) -> UUID:
    """Generate a design from a custom idea, reusing the batch pipeline components."""
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
    from app.services.publishing.printify_publisher import get_base_cost
    from app.utils.storage import storage

    settings_row = db.query(AppSettings).first()
    base_markup = settings_row.base_markup if settings_row else {}
    floor_prices = settings_row.floor_prices if settings_row else {}
    trend_boost_max = float(settings_row.trend_boost_max) if settings_row else 0.20

    # Use preference overrides or classify
    forced_archetype = idea.preferences.get("archetype")
    archetype = forced_archetype if forced_archetype in ("text_only", "illustration", "hybrid", "typographic", "text_icon") else classify_archetype(idea.input_text, "custom")
    image_api = select_image_api(archetype)

    # Create design record (no batch/trend needed for custom ideas)
    design = Design(
        trend_id=None,
        batch_id=None,
        concept_name=idea.input_text[:100],
        archetype=archetype,
        image_api_used=image_api,
        status="generating",
    )
    db.add(design)
    db.commit()
    db.refresh(design)
    design_id = str(design.id)

    # Build image prompt
    image_prompt = build_image_prompt(idea.input_text, archetype, "", idea.input_text[:100])
    design.image_prompt = image_prompt
    db.commit()

    # Generate image
    processed_url = None
    if image_api and image_prompt:
        try:
            raw_bytes, api_used = generate_image(image_prompt, image_api)
            design.image_api_used = api_used
            raw_path = storage.design_raw_path(design_id)
            storage.upload(raw_path, raw_bytes)
            proc_path = storage.design_processed_path(design_id)
            processed_url = storage.upload(proc_path, raw_bytes)
            design.processed_image_url = processed_url
            db.commit()
        except Exception as e:
            logger.warning(f"Image gen failed for custom idea: {e}")
            archetype = "text_only"
            design.archetype = archetype

    # Text content + font
    text_content = generate_text_content(idea.input_text, archetype, "")
    font_result = select_font_pair(idea.input_text, archetype, "", text_content.get("primary_text", ""))
    design.font_pair = font_result["font_pair"]
    design.font_reasoning = font_result["reasoning"]
    design.design_style = archetype

    # Text preview for text-only
    if not processed_url and archetype in ("text_only", "typographic"):
        try:
            from app.services.design.text_preview import generate_text_preview
            preview_bytes = generate_text_preview(
                primary_text=text_content.get("primary_text", idea.input_text),
                secondary_text=text_content.get("secondary_text"),
                font_pair=font_result["font_pair"],
            )
            proc_path = storage.design_processed_path(design_id)
            processed_url = storage.upload(proc_path, preview_bytes)
            design.processed_image_url = processed_url
        except Exception:
            pass

    # Quality score (default for custom ideas)
    design.quality_score = 32
    design.quality_breakdown = {"concept_clarity": 8, "visual_appeal": 8, "merch_suitability": 8, "originality": 8}

    # Shopify copy
    product_types = assign_product_bundle(archetype, design.quality_breakdown)
    copy = generate_shopify_copy(idea.input_text, idea.input_text, archetype, product_types, "")
    design.shopify_title = copy["shopify_title"]
    design.shopify_description = copy["shopify_description"]
    design.shopify_tags = copy["shopify_tags"]
    db.commit()

    # Create products
    for pt in product_types:
        base_cost = get_base_cost(pt)
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

    # Printify tshirt mockup
    image_url = design.processed_image_url
    if image_url:
        tshirt = [p for p in db.new if hasattr(p, 'product_type') and p.product_type == "tshirt"]
        db.commit()
        if tshirt:
            try:
                from app.services.publishing.printify_publisher import _get as _get_printify
                svc = _get_printify()
                printify_id = svc.create_product(
                    product_type="tshirt",
                    title=design.shopify_title or design.concept_name,
                    description="",
                    image_url=image_url,
                    retail_price=float(tshirt[0].retail_price if hasattr(tshirt[0], 'retail_price') else 24.99),
                )
                tshirt_product = db.query(Product).filter(
                    Product.design_id == design.id, Product.product_type == "tshirt"
                ).first()
                if tshirt_product:
                    tshirt_product.printify_product_id = printify_id
                    mockups = svc.generate_mockups(printify_id)
                    tshirt_product.mockup_urls = mockups
            except Exception as e:
                logger.warning(f"Printify mockup failed for custom idea: {e}")
    else:
        db.commit()

    design.status = "ready"
    db.commit()

    return design.id
