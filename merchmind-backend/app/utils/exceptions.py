"""
Typed exception hierarchy for MerchMind.
All service exceptions inherit from MerchMindError so callers can catch broadly or narrowly.
"""


class MerchMindError(Exception):
    """Base exception for all MerchMind errors."""
    pass


# ─── Anthropic / Claude ────────────────────────────────────────────────────────

class ClaudeError(MerchMindError):
    pass

class ClaudeRateLimitError(ClaudeError):
    pass

class ClaudeAPIError(ClaudeError):
    pass

class ClaudeTimeoutError(ClaudeError):
    pass

class ClaudeContentPolicyError(ClaudeError):
    pass


# ─── Image Generation ──────────────────────────────────────────────────────────

class ImageGenerationError(MerchMindError):
    pass

class ContentPolicyRejectionError(ImageGenerationError):
    pass

class ImageGenerationTimeoutError(ImageGenerationError):
    pass

class ImageProviderUnavailableError(ImageGenerationError):
    pass


# ─── Post Processing ───────────────────────────────────────────────────────────

class PostProcessingError(MerchMindError):
    pass

class ContrastCheckFailedError(PostProcessingError):
    pass

class BleedZoneViolationError(PostProcessingError):
    pass


# ─── Storage ───────────────────────────────────────────────────────────────────

class StorageError(MerchMindError):
    pass

class StorageUploadError(StorageError):
    pass

class StorageDownloadError(StorageError):
    pass


# ─── Printify ─────────────────────────────────────────────────────────────────

class PrintifyError(MerchMindError):
    pass

class PrintifyAuthError(PrintifyError):
    pass

class PrintifyRateLimitError(PrintifyError):
    pass

class PrintifyProductError(PrintifyError):
    pass

class PrintifyMockupError(PrintifyError):
    pass


# ─── Shopify ──────────────────────────────────────────────────────────────────

class ShopifyError(MerchMindError):
    pass

class ShopifyAuthError(ShopifyError):
    pass

class ShopifyRateLimitError(ShopifyError):
    pass

class ShopifyProductError(ShopifyError):
    pass

class ShopifyGraphQLError(ShopifyError):
    pass


# ─── Placeit ──────────────────────────────────────────────────────────────────

class PlaceitError(MerchMindError):
    pass

class PlaceitAuthError(PlaceitError):
    pass

class PlaceitTimeoutError(PlaceitError):
    pass

class PlaceitRenderError(PlaceitError):
    pass


# ─── Instagram ────────────────────────────────────────────────────────────────

class InstagramError(MerchMindError):
    pass

class InstagramAuthError(InstagramError):
    pass

class InstagramRateLimitError(InstagramError):
    pass

class InstagramTokenExpiredError(InstagramAuthError):
    pass

class InstagramPostError(InstagramError):
    pass


# ─── TikTok ───────────────────────────────────────────────────────────────────

class TikTokError(MerchMindError):
    pass

class TikTokAuthError(TikTokError):
    pass

class TikTokRateLimitError(TikTokError):
    pass

class TikTokAPITierError(TikTokError):
    """Raised when the account API tier is insufficient for the requested operation."""
    pass


# ─── Pinterest ────────────────────────────────────────────────────────────────

class PinterestError(MerchMindError):
    pass

class PinterestAuthError(PinterestError):
    pass

class PinterestRateLimitError(PinterestError):
    pass

class PinterestTokenExpiredError(PinterestAuthError):
    pass

class PinterestPinError(PinterestError):
    pass


# ─── Klaviyo ──────────────────────────────────────────────────────────────────

class KlaviyoError(MerchMindError):
    pass

class KlaviyoAuthError(KlaviyoError):
    pass

class KlaviyoRateLimitError(KlaviyoError):
    pass

class KlaviyoCampaignError(KlaviyoError):
    pass


# ─── Social Scheduling ────────────────────────────────────────────────────────

class SchedulerError(MerchMindError):
    pass

class PostingLimitExceededError(SchedulerError):
    pass


# ─── Intelligence Scrapers ────────────────────────────────────────────────────

class ScraperError(MerchMindError):
    pass

class GoogleTrendsError(ScraperError):
    pass

class RedditScraperError(ScraperError):
    pass

class TwitterScraperError(ScraperError):
    pass


# ─── Analytics ────────────────────────────────────────────────────────────────

class AnalyticsError(MerchMindError):
    pass

class AnalyticsSyncError(AnalyticsError):
    pass


# ─── Health Monitoring ────────────────────────────────────────────────────────

class HealthCheckError(MerchMindError):
    pass

class CriticalServiceDownError(HealthCheckError):
    """Raised when Anthropic, Printify, or Shopify fail health checks."""
    pass
