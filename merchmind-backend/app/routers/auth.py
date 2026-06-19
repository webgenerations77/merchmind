"""
API key authentication dependency for all protected endpoints.
"""
from fastapi import Header, HTTPException
from app.config import settings


def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    if x_api_key != settings.APP_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key
