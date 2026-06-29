from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/merchmind"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_BUCKET: str = "merchmind"

    # Anthropic
    ANTHROPIC_API_KEY: str = ""

    # OpenAI
    OPENAI_API_KEY: str = ""

    # Replicate
    REPLICATE_API_KEY: str = ""

    # Printify
    PRINTIFY_API_KEY: str = ""
    PRINTIFY_SHOP_ID: str = ""

    # Shopify
    SHOPIFY_STORE_URL: str = ""
    SHOPIFY_ACCESS_TOKEN: str = ""

    # Instagram
    INSTAGRAM_ACCESS_TOKEN: str = ""
    INSTAGRAM_ACCOUNT_ID: str = ""

    # TikTok
    TIKTOK_ACCESS_TOKEN: str = ""

    # Pinterest
    PINTEREST_ACCESS_TOKEN: str = ""

    # Klaviyo
    KLAVIYO_API_KEY: str = ""
    KLAVIYO_LIST_ID: str = ""

    # Placeit (legacy, unused)
    PLACEIT_API_KEY: str = ""

    # Dynamic Mockups
    DYNAMIC_MOCKUPS_API_KEY: str = ""

    # Ideogram
    IDEOGRAM_API_KEY: str = ""

    # Firecrawl (web-search trend source)
    FIRECRAWL_API_KEY: str = ""

    # Expo Push
    EXPO_ACCESS_TOKEN: str = ""

    # Shopify Store 1 (primary / Spinach The Cow HQ)
    STORE_1_NAME: str = "Spinach The Cow"
    STORE_1_SHOPIFY_URL: str = ""
    STORE_1_ACCESS_TOKEN: str = ""

    # Shopify Store 2 (secondary / overflow store)
    STORE_2_NAME: str = "Store 2"
    STORE_2_SHOPIFY_URL: str = ""
    STORE_2_ACCESS_TOKEN: str = ""

    # Generator cost config (USD per image, for UI display)
    DALLE3_COST_PER_IMAGE: float = 0.04
    IDEOGRAM_COST_PER_IMAGE: float = 0.08
    FLUX_SCHNELL_COST_PER_IMAGE: float = 0.003

    # Batch settings
    # Mandatory by default: every trend-based batch pauses at the approval gate
    # after scoring so no design is generated without human trend approval.
    # (Custom flows — Drew's Mind, Collections — have their own paths and are unaffected.)
    REQUIRE_TREND_APPROVAL: bool = True

    # Printify catalog cache
    PRINTIFY_CATALOG_TTL_HOURS: int = 24
    PRINTIFY_MAX_COLORS_PER_PRODUCT: int = 25

    # App
    APP_API_KEY: str = "dev-api-key"
    ENVIRONMENT: str = "development"

    # Model routing
    HAIKU_MODEL: str = "claude-haiku-4-5-20251001"
    SONNET_MODEL: str = "claude-sonnet-4-6"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
