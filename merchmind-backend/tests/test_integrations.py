"""
Integration tests for all external service integrations.
Uses respx to mock httpx calls — no real network requests.
"""
import pytest
import respx
import httpx
from unittest.mock import patch, MagicMock


# ─── UTM Builder ──────────────────────────────────────────────────────────────

def test_utm_builder_instagram():
    from app.utils.utm_builder import instagram_url
    url = instagram_url("https://myshop.com/products/dog-tee", campaign="golden-retriever-energy", content="post")
    assert "utm_source=instagram" in url
    assert "utm_medium=social" in url
    assert "utm_campaign=golden-retriever-energy" in url
    assert "utm_content=post" in url


def test_utm_builder_email():
    from app.utils.utm_builder import email_url
    url = email_url("https://myshop.com/products/dog-tee", campaign="Drop Launch")
    assert "utm_source=klaviyo" in url
    assert "utm_medium=email" in url
    assert "utm_campaign=drop-launch" in url


def test_utm_builder_preserves_existing_params():
    from app.utils.utm_builder import build_utm_url
    url = build_utm_url("https://myshop.com/?ref=hero", source="ig", medium="social", campaign="test")
    assert "ref=hero" in url
    assert "utm_source=ig" in url


# ─── Exception Hierarchy ─────────────────────────────────────────────────────

def test_exception_hierarchy():
    from app.utils.exceptions import (
        MerchMindError, PrintifyError, PrintifyAuthError,
        ShopifyError, ShopifyAuthError, ImageGenerationError, ContentPolicyRejectionError,
    )
    assert issubclass(PrintifyError, MerchMindError)
    assert issubclass(PrintifyAuthError, PrintifyError)
    assert issubclass(ShopifyAuthError, ShopifyError)
    assert issubclass(ContentPolicyRejectionError, ImageGenerationError)
    assert issubclass(ImageGenerationError, MerchMindError)


# ─── Printify Service ─────────────────────────────────────────────────────────

@respx.mock
def test_printify_health_check_ok():
    import app.services.publishing.printify_publisher as pp_module
    from app.services.publishing.printify_publisher import PrintifyService
    with patch.object(pp_module, "settings") as mock_settings:
        mock_settings.PRINTIFY_API_KEY = "test-key"
        mock_settings.PRINTIFY_SHOP_ID = "test-shop-id"
        respx.get("https://api.printify.com/v1/shops/test-shop-id.json").mock(
            return_value=httpx.Response(200, json={"id": "test-shop-id", "title": "Test Shop"})
        )
        svc = PrintifyService()
        result = svc.health_check()
    assert result["service"] == "printify"
    assert result["ok"] is True


@respx.mock
def test_printify_auth_error():
    import app.services.publishing.printify_publisher as pp_module
    from app.utils.exceptions import PrintifyAuthError
    from app.services.publishing.printify_publisher import PrintifyService
    with patch.object(pp_module, "settings") as mock_settings:
        mock_settings.PRINTIFY_API_KEY = "bad-key"
        mock_settings.PRINTIFY_SHOP_ID = "shop"
        respx.get("https://api.printify.com/v1/shops/shop.json").mock(
            return_value=httpx.Response(401, json={"error": "Unauthorized"})
        )
        svc = PrintifyService()
        with pytest.raises(PrintifyAuthError):
            svc._request("GET", "/shops/shop.json")


# ─── Shopify Service ──────────────────────────────────────────────────────────

@respx.mock
def test_shopify_health_check_ok():
    from app.services.publishing.shopify_publisher import ShopifyService
    svc = ShopifyService()
    with patch("app.config.settings") as mock_settings:
        mock_settings.SHOPIFY_STORE_URL = "mystore.myshopify.com"
        mock_settings.SHOPIFY_ACCESS_TOKEN = "test-token"
        respx.get("https://mystore.myshopify.com/admin/api/2024-01/shop.json").mock(
            return_value=httpx.Response(200, json={"shop": {"id": 123, "name": "Test"}})
        )
        result = svc.health_check()
    assert result["service"] == "shopify"


@respx.mock
def test_shopify_graphql():
    import app.services.publishing.shopify_publisher as sp_module
    from app.services.publishing.shopify_publisher import ShopifyService
    with patch.object(sp_module, "settings") as mock_settings:
        mock_settings.SHOPIFY_STORE_URL = "mystore.myshopify.com"
        mock_settings.SHOPIFY_ACCESS_TOKEN = "test-token"
        respx.post("https://mystore.myshopify.com/admin/api/2024-01/graphql.json").mock(
            return_value=httpx.Response(200, json={"data": {"metafieldsSet": {"metafields": [], "userErrors": []}}})
        )
        svc = ShopifyService()
        svc.set_metafields("123", {"niche": "pets"})


# ─── Instagram Service ────────────────────────────────────────────────────────

@respx.mock
def test_instagram_schedule_post():
    from app.services.marketing.instagram_service import InstagramService
    svc = InstagramService()
    svc._token = "test-token"
    svc._account_id = "123"
    svc._token_expires_at = None

    respx.post("https://graph.facebook.com/v19.0/123/media").mock(
        return_value=httpx.Response(200, json={"id": "container-1"})
    )
    respx.post("https://graph.facebook.com/v19.0/123/media_publish").mock(
        return_value=httpx.Response(200, json={"id": "media-1"})
    )
    media_id = svc.schedule_post(
        image_url="https://example.com/img.png",
        caption="Test caption",
        product_url="https://myshop.com/product",
        campaign="test-campaign",
    )
    assert media_id == "media-1"


@respx.mock
def test_instagram_health_check_ok():
    from app.services.marketing.instagram_service import InstagramService
    svc = InstagramService()
    svc._token = "test-token"
    svc._account_id = "123"
    svc._token_expires_at = None

    respx.get("https://graph.facebook.com/v19.0/123").mock(
        return_value=httpx.Response(200, json={"id": "123", "name": "MerchMind"})
    )
    result = svc.health_check()
    assert result["ok"] is True


# ─── TikTok Service ───────────────────────────────────────────────────────────

def test_tiktok_skips_without_token():
    from app.services.marketing.tiktok_service import TikTokService
    svc = TikTokService()
    with patch("app.config.settings") as mock_settings:
        mock_settings.TIKTOK_ACCESS_TOKEN = ""
        result = svc.post_video(
            video_url="https://example.com/video.mp4",
            caption="test",
            product_url="https://myshop.com/product",
            campaign="test",
        )
    assert result is None


@respx.mock
def test_tiktok_tier_error_graceful():
    from app.services.marketing.tiktok_service import TikTokService
    svc = TikTokService()
    respx.post("https://open.tiktokapis.com/v2/post/publish/video/init/").mock(
        return_value=httpx.Response(403, json={"error": {"code": 4000, "message": "Not permitted"}})
    )
    with patch("app.config.settings") as mock_settings:
        mock_settings.TIKTOK_ACCESS_TOKEN = "some-token"
        result = svc.post_video(
            video_url="https://example.com/video.mp4",
            caption="test",
            product_url="https://myshop.com/product",
            campaign="test",
        )
    assert result is None


# ─── Pinterest Service ────────────────────────────────────────────────────────

@respx.mock
def test_pinterest_create_pin():
    from app.services.marketing.pinterest_service import PinterestService
    svc = PinterestService()
    svc._token = "test-token"
    svc._token_expires_at = None

    respx.post("https://api.pinterest.com/v5/pins").mock(
        return_value=httpx.Response(201, json={"id": "pin-abc"})
    )
    pin_id = svc.create_pin(
        board_id="board-1",
        title="Dog Tee",
        description="Cute dog tee for dog lovers",
        image_url="https://example.com/img.png",
        product_url="https://myshop.com/product",
        campaign="golden-retriever",
    )
    assert pin_id == "pin-abc"


@respx.mock
def test_pinterest_ensure_board_exists_creates():
    from app.services.marketing.pinterest_service import PinterestService
    svc = PinterestService()
    svc._token = "test-token"
    svc._token_expires_at = None

    respx.get("https://api.pinterest.com/v5/boards").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    respx.post("https://api.pinterest.com/v5/boards").mock(
        return_value=httpx.Response(201, json={"id": "new-board"})
    )
    board_id = svc.ensure_board_exists("Pets Collection")
    assert board_id == "new-board"


# ─── Klaviyo Service ──────────────────────────────────────────────────────────

@respx.mock
def test_klaviyo_build_email_html():
    from app.services.marketing.klaviyo_service import KlaviyoService
    svc = KlaviyoService()
    html = svc.build_product_launch_email(
        design_title="Golden Retriever Energy",
        tagline="Vibes only.",
        product_url="https://myshop.com/products/test",
        image_url="https://cdn.example.com/img.png",
        price=24.99,
        campaign="golden-retriever-energy",
        niche="pets",
    )
    assert "Golden Retriever Energy" in html
    assert "utm_source=klaviyo" in html
    assert "$24.99" in html
    assert "Shop Now" in html


@respx.mock
def test_klaviyo_health_check_ok():
    from app.services.marketing.klaviyo_service import KlaviyoService
    svc = KlaviyoService()
    respx.get("https://a.klaviyo.com/api/accounts/").mock(
        return_value=httpx.Response(200, json={"data": [{"id": "acc-1"}]})
    )
    with patch("app.config.settings") as mock_settings:
        mock_settings.KLAVIYO_API_KEY = "test-key"
        result = svc.health_check()
    assert result["service"] == "klaviyo"


# ─── Social Scheduler ─────────────────────────────────────────────────────────

def test_scheduler_optimal_time_pets():
    from app.services.marketing.scheduler import SocialScheduler
    from datetime import datetime, timezone
    svc = SocialScheduler()
    base = datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)  # 5am Eastern
    t = svc.get_optimal_time("instagram", "pets", base_time=base)
    assert t > base


def test_scheduler_posting_limit():
    from app.services.marketing.scheduler import SocialScheduler
    from app.utils.exceptions import PostingLimitExceededError
    svc = SocialScheduler()
    with pytest.raises(PostingLimitExceededError):
        svc.check_posting_limit("instagram", posts_today=10)


def test_scheduler_posting_limit_ok():
    from app.services.marketing.scheduler import SocialScheduler
    svc = SocialScheduler()
    svc.check_posting_limit("instagram", posts_today=0)  # should not raise


# ─── Image Generator ──────────────────────────────────────────────────────────

def test_image_generator_content_policy_propagates():
    from app.services.design.image_generator import DALLe3Service
    from app.utils.exceptions import ContentPolicyRejectionError
    from openai import BadRequestError as OpenAIBadRequestError

    svc = DALLe3Service()

    async def _raise(*a, **kw):
        # Build a real httpx.Response so BadRequestError doesn't fail to construct
        req = httpx.Request("POST", "https://api.openai.com/v1/images/generations")
        resp = httpx.Response(
            400,
            json={"error": {"type": "content_policy_violation", "message": "content_policy_violation"}},
            request=req,
        )
        raise OpenAIBadRequestError(
            message="content_policy_violation",
            response=resp,
            body={"error": {"type": "content_policy_violation"}},
        )

    import asyncio
    with patch.object(svc._client.images, "generate", side_effect=_raise):
        with pytest.raises(ContentPolicyRejectionError):
            asyncio.run(svc.generate("bad prompt"))


# ─── Health Router ────────────────────────────────────────────────────────────

def test_health_endpoint_public():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import app.routers.health as health_module
    from app.routers.health import router as health_router

    mini_app = FastAPI()
    mini_app.include_router(health_router)

    with patch.object(health_module, "settings") as mock_settings:
        mock_settings.ENVIRONMENT = "test"
        client = TestClient(mini_app)
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True
