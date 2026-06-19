"""
API key authentication dependency for all protected endpoints.
"""
from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader
from app.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key")


def verify_api_key(x_api_key: str = Depends(_api_key_header)) -> str:
    if x_api_key != settings.APP_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key
