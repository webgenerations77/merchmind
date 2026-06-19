"""
UTM parameter builder for all outbound links.
Every link posted to social or email must carry UTM tracking.
"""
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs, urlencode as qs_encode
from typing import Literal

Channel = Literal["instagram", "tiktok", "pinterest", "email", "blog", "organic"]


def build_utm_url(
    url: str,
    source: str,
    medium: Channel,
    campaign: str,
    content: str | None = None,
    term: str | None = None,
) -> str:
    """
    Append UTM parameters to a URL, preserving any existing query params.

    Args:
        url: The destination URL (e.g., Shopify product URL)
        source: Traffic source (e.g., 'instagram', 'pinterest', 'klaviyo')
        medium: Marketing medium (e.g., 'social', 'email')
        campaign: Campaign name — use the design concept name or batch date (e.g., 'golden-retriever-energy')
        content: Optional ad variant differentiator (e.g., 'reel', 'story', 'pin')
        term: Optional keyword (e.g., niche cluster name)
    """
    parsed = urlparse(url)
    params = {
        "utm_source": source,
        "utm_medium": medium,
        "utm_campaign": _slugify(campaign),
    }
    if content:
        params["utm_content"] = _slugify(content)
    if term:
        params["utm_term"] = _slugify(term)

    existing_qs = parsed.query
    if existing_qs:
        query = existing_qs + "&" + urlencode(params)
    else:
        query = urlencode(params)

    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, query, parsed.fragment))


def instagram_url(url: str, campaign: str, content: str | None = None) -> str:
    return build_utm_url(url, source="instagram", medium="social", campaign=campaign, content=content)


def tiktok_url(url: str, campaign: str, content: str | None = None) -> str:
    return build_utm_url(url, source="tiktok", medium="social", campaign=campaign, content=content)


def pinterest_url(url: str, campaign: str, content: str | None = None) -> str:
    return build_utm_url(url, source="pinterest", medium="social", campaign=campaign, content=content)


def email_url(url: str, campaign: str, content: str | None = None) -> str:
    return build_utm_url(url, source="klaviyo", medium="email", campaign=campaign, content=content)


def blog_url(url: str, campaign: str) -> str:
    return build_utm_url(url, source="blog", medium="organic", campaign=campaign)


def _slugify(text: str) -> str:
    return text.lower().replace(" ", "-").replace("_", "-")
