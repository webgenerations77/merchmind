"""
Supabase Storage wrapper for design assets and mockups.
Supabase client is instantiated lazily so the module can be imported without credentials.
"""
import logging
import os
from pathlib import Path

from supabase import create_client, Client

logger = logging.getLogger(__name__)

_supabase_client = None


def _get_client() -> Client:
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(
            os.environ.get("SUPABASE_URL"),
            os.environ.get("SUPABASE_KEY"),
        )
    return _supabase_client


def _bucket_name() -> str:
    return os.environ.get("SUPABASE_BUCKET", "merchmind")


def _public_url(storage_path: str) -> str:
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    return f"{base}/storage/v1/object/public/{_bucket_name()}/{storage_path}"


# ---------------------------------------------------------------------------
# Async module-level API
# ---------------------------------------------------------------------------

async def upload_file(local_path: str, storage_path: str) -> str:
    """Upload a local file to Supabase Storage. Returns public URL."""
    data = Path(local_path).read_bytes()
    return await upload_bytes(data, storage_path)


async def upload_bytes(data: bytes, storage_path: str, content_type: str = "image/png") -> str:
    """Upload bytes directly to Supabase Storage. Returns public URL."""
    try:
        client = _get_client()
        client.storage.from_(_bucket_name()).upload(
            storage_path,
            data,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        url = _public_url(storage_path)
        logger.info("storage.upload_bytes path=%s", storage_path)
        return url
    except Exception as e:
        raise RuntimeError(f"Failed to upload '{storage_path}' to Supabase Storage: {e}") from e


async def delete_file(storage_path: str) -> bool:
    """Delete a file from Supabase Storage. Returns True on success, False if not found."""
    try:
        client = _get_client()
        client.storage.from_(_bucket_name()).remove([storage_path])
        logger.info("storage.delete_file path=%s", storage_path)
        return True
    except Exception as e:
        logger.error("storage.delete_file failed path=%s error=%s", storage_path, e)
        return False


async def file_exists(storage_path: str) -> bool:
    """Check if a file exists in Supabase Storage."""
    try:
        client = _get_client()
        client.storage.from_(_bucket_name()).download(storage_path)
        return True
    except Exception:
        return False


async def health_check() -> bool:
    """Validate Supabase credentials by listing the bucket root."""
    try:
        client = _get_client()
        client.storage.from_(_bucket_name()).list()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Synchronous class-based API (used by Celery tasks and services)
# ---------------------------------------------------------------------------

class StorageClient:
    def __init__(self):
        self._bucket = None

    @property
    def bucket(self):
        if self._bucket is None:
            self._bucket = _bucket_name()
        return self._bucket

    def upload(self, path: str, data: bytes, content_type: str = "image/png") -> str:
        """Upload bytes to storage and return the public URL."""
        try:
            client = _get_client()
            client.storage.from_(self.bucket).upload(
                path,
                data,
                file_options={"content-type": content_type, "upsert": "true"},
            )
            result = client.storage.from_(self.bucket).get_public_url(path)
            logger.info("storage.upload path=%s", path)
            return result
        except Exception as e:
            raise RuntimeError(f"Failed to upload '{path}' to Supabase Storage: {e}") from e

    def upload_file(self, path: str, local_path: str, content_type: str = "image/png") -> str:
        """Upload a local file to storage and return the public URL."""
        data = Path(local_path).read_bytes()
        return self.upload(path, data, content_type)

    def download(self, path: str) -> bytes:
        """Download bytes from storage."""
        try:
            return _get_client().storage.from_(self.bucket).download(path)
        except Exception as e:
            raise RuntimeError(f"Failed to download '{path}' from Supabase Storage: {e}") from e

    def delete(self, path: str) -> None:
        """Delete a file from storage."""
        try:
            _get_client().storage.from_(self.bucket).remove([path])
        except Exception as e:
            raise RuntimeError(f"Failed to delete '{path}' from Supabase Storage: {e}") from e

    def design_raw_path(self, design_id: str) -> str:
        return f"designs/{design_id}/raw.png"

    def design_processed_path(self, design_id: str) -> str:
        return f"designs/{design_id}/processed.png"

    def mockup_path(self, design_id: str, product_type: str, variant: str = "front") -> str:
        return f"designs/{design_id}/mockups/{product_type}/{variant}.png"


storage = StorageClient()
