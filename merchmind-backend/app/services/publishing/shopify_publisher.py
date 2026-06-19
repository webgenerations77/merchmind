"""
Shopify API client — class-based service.
REST for standard CRUD, GraphQL Admin API 2024-01 for bulk ops and metafields.
Leaky bucket rate limiter: 2 REST calls/sec, 50 GraphQL points/sec.
"""
import logging
import time
from collections import deque
from functools import lru_cache
from threading import Lock
from typing import Any

import httpx

from app.config import settings
from app.utils.exceptions import (
    ShopifyAuthError,
    ShopifyError,
    ShopifyGraphQLError,
    ShopifyProductError,
    ShopifyRateLimitError,
)

logger = logging.getLogger(__name__)

_TIMEOUT = 30
_MAX_RETRIES = 3
_GRAPHQL_API = "2024-01"


class LeakyBucketLimiter:
    """Token-based leaky bucket: `rate` calls per second."""
    def __init__(self, rate: float) -> None:
        self._rate = rate
        self._min_interval = 1.0 / rate
        self._last_call = 0.0
        self._lock = Lock()

    def consume(self) -> None:
        with self._lock:
            now = time.monotonic()
            wait = self._min_interval - (now - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.monotonic()


_rest_limiter = LeakyBucketLimiter(rate=2.0)
_graphql_point_budget = 50


class ShopifyService:
    def _rest_url(self, path: str) -> str:
        base = settings.SHOPIFY_STORE_URL.rstrip("/")
        if not base.startswith("https://"):
            base = f"https://{base}"
        return f"{base}/admin/api/2024-01/{path}"

    def _graphql_url(self) -> str:
        base = settings.SHOPIFY_STORE_URL.rstrip("/")
        if not base.startswith("https://"):
            base = f"https://{base}"
        return f"{base}/admin/api/{_GRAPHQL_API}/graphql.json"

    def _headers(self) -> dict:
        return {
            "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = self._rest_url(path)
        for attempt in range(_MAX_RETRIES):
            start = time.monotonic()
            try:
                _rest_limiter.consume()
                with httpx.Client(timeout=_TIMEOUT) as client:
                    response = client.request(method, url, headers=self._headers(), **kwargs)
                elapsed = round((time.monotonic() - start) * 1000)
                logger.info("shopify.rest method=%s path=%s status=%d ms=%d", method, path, response.status_code, elapsed)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                code = e.response.status_code
                if code == 401:
                    raise ShopifyAuthError(f"Shopify auth failed on {method} {path}") from e
                if code == 429:
                    retry_after = float(e.response.headers.get("Retry-After", 2 ** attempt * 5))
                    logger.warning("shopify.rate_limit wait=%.1fs attempt=%d", retry_after, attempt + 1)
                    time.sleep(retry_after)
                    continue
                raise ShopifyProductError(f"Shopify {code} on {method} {path}: {e.response.text[:300]}") from e
            except ShopifyAuthError:
                raise
            except Exception as e:
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(2 ** attempt * 2)
                    continue
                raise ShopifyError(f"Shopify request failed after {_MAX_RETRIES} attempts: {e}") from e
        raise ShopifyError("Shopify: max retries exceeded")

    def _graphql(self, query: str, variables: dict | None = None) -> dict:
        start = time.monotonic()
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                response = client.post(
                    self._graphql_url(),
                    headers=self._headers(),
                    json={"query": query, "variables": variables or {}},
                )
            elapsed = round((time.monotonic() - start) * 1000)
            response.raise_for_status()
            data = response.json()
            logger.info("shopify.graphql status=%d ms=%d", response.status_code, elapsed)

            if "errors" in data:
                raise ShopifyGraphQLError(f"Shopify GraphQL errors: {data['errors']}")

            # Respect query cost throttling
            throttle = data.get("extensions", {}).get("cost", {})
            requested = throttle.get("requestedQueryCost", 0)
            available = throttle.get("throttleStatus", {}).get("currentlyAvailable", _graphql_point_budget)
            if available < requested * 2:
                restore_rate = throttle.get("throttleStatus", {}).get("restoreRate", 50)
                wait = max(0.1, requested / max(restore_rate, 1))
                logger.info("shopify.graphql throttle wait=%.2fs available=%d requested=%d", wait, available, requested)
                time.sleep(wait)

            return data.get("data", {})
        except ShopifyGraphQLError:
            raise
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ShopifyAuthError("Shopify GraphQL auth failed") from e
            raise ShopifyGraphQLError(f"Shopify GraphQL HTTP {e.response.status_code}: {e.response.text[:300]}") from e

    def create_product_draft(
        self,
        title: str,
        description: str,
        tags: list[str],
        price: float,
        image_urls: list[str] | None = None,
        vendor: str = "MerchMind",
    ) -> str:
        payload = {
            "product": {
                "title": title,
                "body_html": description,
                "vendor": vendor,
                "tags": ", ".join(tags),
                "status": "draft",
                "variants": [
                    {
                        "price": str(round(price, 2)),
                        "inventory_management": "shopify",
                        "fulfillment_service": "manual",
                    }
                ],
            }
        }
        if image_urls:
            payload["product"]["images"] = [{"src": url} for url in image_urls[:10]]

        result = self._request("POST", "products.json", json=payload)
        product_id = str(result.get("product", {}).get("id", ""))
        if not product_id:
            raise ShopifyProductError(f"Shopify create_product returned no ID: {result}")
        logger.info("shopify.create_product_draft product_id=%s title=%r", product_id, title)
        return product_id

    def activate_product(self, shopify_product_id: str) -> None:
        self._request(
            "PUT",
            f"products/{shopify_product_id}.json",
            json={"product": {"id": shopify_product_id, "status": "active"}},
        )
        logger.info("shopify.activate_product product_id=%s", shopify_product_id)

    def unpublish_product(self, shopify_product_id: str) -> None:
        self._request(
            "PUT",
            f"products/{shopify_product_id}.json",
            json={"product": {"id": shopify_product_id, "status": "draft"}},
        )
        logger.info("shopify.unpublish_product product_id=%s", shopify_product_id)

    def update_product_price(self, shopify_product_id: str, variant_id: str, new_price: float) -> None:
        self._request(
            "PUT",
            f"variants/{variant_id}.json",
            json={"variant": {"id": variant_id, "price": str(round(new_price, 2))}},
        )
        logger.info("shopify.update_price product_id=%s variant_id=%s price=%.2f", shopify_product_id, variant_id, new_price)

    def set_metafields(self, product_id: str, metafields: dict) -> None:
        """Set product metafields via GraphQL mutations."""
        inputs = [
            {
                "ownerId": f"gid://shopify/Product/{product_id}",
                "namespace": "merchmind",
                "key": key,
                "value": str(value),
                "type": "single_line_text_field",
            }
            for key, value in metafields.items()
        ]
        mutation = """
        mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
            metafieldsSet(metafields: $metafields) {
                metafields { id key value }
                userErrors { field message }
            }
        }
        """
        data = self._graphql(mutation, {"metafields": inputs})
        errors = data.get("metafieldsSet", {}).get("userErrors", [])
        if errors:
            logger.warning("shopify.set_metafields errors=%s", errors)

    def create_blog_post(self, title: str, body_html: str, tags: list[str], blog_id: str | None = None) -> str:
        """Create a Shopify blog article. Returns article ID."""
        if not blog_id:
            blogs = self._request("GET", "blogs.json")
            blog_list = blogs.get("blogs", [])
            if not blog_list:
                raise ShopifyError("No blogs found in Shopify store")
            blog_id = str(blog_list[0]["id"])

        payload = {
            "article": {
                "title": title,
                "body_html": body_html,
                "tags": ", ".join(tags),
                "published": True,
            }
        }
        result = self._request("POST", f"blogs/{blog_id}/articles.json", json=payload)
        article_id = str(result.get("article", {}).get("id", ""))
        logger.info("shopify.create_blog_post article_id=%s title=%r", article_id, title)
        return article_id

    def get_sales_since(self, since_date: str) -> list[dict]:
        """Fetch orders since ISO date string. Follows cursor pagination."""
        orders: list[dict] = []
        url = f"orders.json?status=any&created_at_min={since_date}&limit=250"
        while url:
            result = self._request("GET", url)
            batch = result.get("orders", [])
            orders.extend(batch)
            # TODO: parse Link header for cursor pagination when > 250 orders
            break
        logger.info("shopify.get_sales_since since=%s orders=%d", since_date, len(orders))
        return orders

    def health_check(self) -> dict:
        try:
            start = time.monotonic()
            result = self._request("GET", "shop.json")
            ms = round((time.monotonic() - start) * 1000)
            ok = bool(result.get("shop", {}).get("id"))
            return {"service": "shopify", "ok": ok, "ms": ms}
        except ShopifyAuthError as e:
            return {"service": "shopify", "ok": False, "error": "auth_failed", "detail": str(e)}
        except Exception as e:
            logger.warning("shopify.health_check failed error=%s", e)
            return {"service": "shopify", "ok": False, "error": str(e)}


@lru_cache(maxsize=1)
def get_shopify_service() -> ShopifyService:
    return ShopifyService()


# ─── Module-level aliases for backwards compatibility ─────────────────────────

_svc: ShopifyService | None = None


def _get() -> ShopifyService:
    global _svc
    if _svc is None:
        _svc = ShopifyService()
    return _svc


def create_product_draft(title, description, tags, price, image_urls=None, vendor="MerchMind") -> str:
    return _get().create_product_draft(title, description, tags, price, image_urls, vendor)


def activate_product(shopify_product_id: str) -> None:
    _get().activate_product(shopify_product_id)


def unpublish_product(shopify_product_id: str) -> None:
    _get().unpublish_product(shopify_product_id)


def get_sales_since(since_date: str) -> list[dict]:
    return _get().get_sales_since(since_date)


def update_product_price(shopify_product_id: str, variant_id: str, new_price: float) -> None:
    _get().update_product_price(shopify_product_id, variant_id, new_price)
