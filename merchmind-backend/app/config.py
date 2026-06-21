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

    # Expo Push
    EXPO_ACCESS_TOKEN: str = ""

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
