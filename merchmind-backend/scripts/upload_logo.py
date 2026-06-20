"""
Upload Spinach the Cow logo to Supabase and update AppSettings.back_logo_url.

Usage: python scripts/upload_logo.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from app.utils.storage import storage
from app.database import SessionLocal
from app.models.settings import AppSettings
from app.models.collection import Collection  # noqa: F401 — needed for relationship resolution

LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "merchmind-app", "assets", "Logo.png")
STORAGE_PATH = "branding/spinach_logo.png"


def main():
    logo_path = os.path.abspath(LOGO_PATH)
    if not os.path.exists(logo_path):
        print(f"Logo not found at {logo_path}")
        sys.exit(1)

    print(f"Uploading {logo_path} to Supabase as {STORAGE_PATH}...")
    url = storage.upload_file(STORAGE_PATH, logo_path)
    print(f"Uploaded: {url}")

    db = SessionLocal()
    try:
        settings = db.query(AppSettings).first()
        if settings:
            settings.back_logo_url = url
            settings.back_logo_enabled = True
            settings.back_logo_products = ["tshirt", "hat"]
            db.commit()
            print("Updated AppSettings: back_logo_enabled=True, back_logo_url set")
        else:
            print("No AppSettings row found — run seed.py first")
    finally:
        db.close()


if __name__ == "__main__":
    main()
