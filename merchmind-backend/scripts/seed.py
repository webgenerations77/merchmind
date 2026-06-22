"""
Seed script: creates settings, niche clusters, and 3 sample designs
for mobile app development without running the full pipeline.

Usage: python scripts/seed.py
"""
import sys
import os
import uuid
from datetime import datetime, date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal, engine, Base
from app.models.niche_cluster import NicheCluster
from app.models.settings import AppSettings
from app.models.batch import Batch
from app.models.trend import Trend
from app.models.design import Design
from app.models.product import Product
from app.models.marketing_asset import MarketingAsset

Base.metadata.create_all(bind=engine)


def seed():
    db = SessionLocal()
    try:
        # Skip if already seeded
        if db.query(AppSettings).first():
            print("Database already seeded. Skipping.")
            return

        print("Seeding niche clusters...")
        clusters = [
            NicheCluster(
                name="Pet Obsessed", emoji="🐾",
                subreddits=["dogs", "cats", "AnimalsBeingDerps", "corgi", "goldenretrievers"],
                keywords=["dog mom", "cat dad", "fur baby", "golden retriever", "corgi", "dachshund"],
                score_boost=15, active=True,
            ),
            NicheCluster(
                name="Work & Hustle Humor", emoji="☕",
                subreddits=["antiwork", "WorkReform", "nurses", "Teachers", "cscareerquestions"],
                keywords=["Monday", "coffee", "overtime", "I survived", "meetings", "adulting"],
                score_boost=15, active=True,
            ),
            NicheCluster(
                name="Outdoor & Adventure", emoji="🌿",
                subreddits=["hiking", "camping", "climbing", "MountainBiking", "NationalParks"],
                keywords=["trail life", "summit", "van life", "leave no trace", "nature heals"],
                score_boost=15, active=False,
            ),
            NicheCluster(
                name="Gamer & Nerd Culture", emoji="🎮",
                subreddits=["gaming", "pcmasterrace", "DnD", "boardgames", "anime"],
                keywords=["GG", "respawn", "critical hit", "level up", "nerd", "geek pride"],
                score_boost=15, active=False,
            ),
            NicheCluster(
                name="Wellness & Mindset", emoji="🧘",
                subreddits=["Meditation", "yoga", "running", "loseit", "getdisciplined"],
                keywords=["mental health", "self care", "growth mindset", "marathon", "marathon mom"],
                score_boost=15, active=False,
            ),
        ]
        for c in clusters:
            db.add(c)
        db.commit()
        print(f"  Created {len(clusters)} niche clusters")

        active_ids = [str(c.id) for c in clusters if c.active]

        print("Seeding settings...")
        settings = AppSettings(
            base_markup={"tshirt": 2.5, "mug": 2.8, "hat": 2.5, "phone_case": 2.5, "sticker": 3.0},
            floor_prices={"tshirt": 24.99, "mug": 18.99, "hat": 26.99, "phone_case": 22.99, "sticker": 6.99},
            trend_boost_max=0.20,
            batch_day="sunday",
            min_queue_size=10,
            max_queue_size=25,
            quality_threshold=28,
            score_threshold=35,
            underperform_weeks=4,
            active_clusters=[c.id for c in clusters if c.active],
        )
        db.add(settings)
        db.commit()
        print("  Settings created")

        print("Seeding test batch and sample designs...")
        batch = Batch(
            week_start=date.today(),
            run_started_at=datetime.utcnow(),
            run_completed_at=datetime.utcnow(),
            status="complete",
            total_ideas=50,
            queued_count=3,
            approved_count=0,
            rejected_count=47,
            delayed_count=0,
        )
        db.add(batch)
        db.commit()

        sample_designs = [
            {
                "raw_signal": "dog mom life is the best life",
                "archetype": "text_only",
                "concept_name": "Dog Mom Life",
                "shopify_title": "Dog Mom Life Is The Best Life T-Shirt",
                "shopify_description": "For the dog mom who wouldn't have it any other way. This cozy tee captures the joy of the fur baby life with bold, heartfelt typography that every dog lover will instantly connect with.",
                "shopify_tags": ["dog mom", "dog gift", "fur baby", "pet lover", "dog owner"],
                "quality_score": 32,
                "quality_breakdown": {"concept_clarity": 9, "visual_appeal": 7, "merch_suitability": 9, "originality": 7},
                "final_score": 78,
                "product_types": ["tshirt", "mug", "hat", "phone_case", "sticker"],
            },
            {
                "raw_signal": "I survived another meeting that could have been an email",
                "archetype": "typographic",
                "concept_name": "Meeting Survivor",
                "shopify_title": "Survived Another Meeting That Could've Been An Email",
                "shopify_description": "The only thing worse than a Monday meeting? A meeting about scheduling meetings. This bold typographic design speaks for every office worker's soul.",
                "shopify_tags": ["office humor", "work life", "meeting survivor", "adulting", "coworker gift"],
                "quality_score": 34,
                "quality_breakdown": {"concept_clarity": 9, "visual_appeal": 8, "merch_suitability": 9, "originality": 8},
                "final_score": 82,
                "product_types": ["tshirt", "mug", "sticker"],
            },
            {
                "raw_signal": "golden retriever energy every day",
                "archetype": "illustration",
                "concept_name": "Golden Retriever Energy",
                "shopify_title": "Golden Retriever Energy — Happy Every Day T-Shirt",
                "shopify_description": "Pure joy. Boundless enthusiasm. Zero bad days. This cheerful golden retriever illustration captures the contagious optimism of the world's most lovable dog breed.",
                "shopify_tags": ["golden retriever", "dog lover", "happy vibes", "puppy", "dog illustration"],
                "quality_score": 30,
                "quality_breakdown": {"concept_clarity": 8, "visual_appeal": 8, "merch_suitability": 7, "originality": 7},
                "final_score": 71,
                "product_types": ["tshirt", "sticker"],
            },
        ]

        for i, sd in enumerate(sample_designs):
            trend = Trend(
                batch_id=batch.id,
                source="reddit",
                raw_signal=sd["raw_signal"],
                source_metadata={"subreddit": "dogs" if "dog" in sd["raw_signal"] else "antiwork", "score": 2500},
                trend_score=70 + i * 5,
                viability_score=75 + i * 3,
                final_score=sd["final_score"],
                claude_reasoning=f"Strong niche appeal with clear visual potential and emotional resonance.",
                risk_flag="none",
                status="queued",
            )
            db.add(trend)
            db.flush()

            design = Design(
                trend_id=trend.id,
                batch_id=batch.id,
                concept_name=sd["concept_name"],
                archetype=sd["archetype"],
                shopify_title=sd["shopify_title"],
                shopify_description=sd["shopify_description"],
                shopify_tags=sd["shopify_tags"],
                quality_score=sd["quality_score"],
                quality_breakdown=sd["quality_breakdown"],
                font_pair="Bebas Neue / Montserrat",
                color_palette=["#1a1a1a", "#ffffff", "#e74c3c", "#f39c12"],
                status="ready",
            )
            db.add(design)
            db.flush()

            for pt in sd["product_types"]:
                base_cost = {"tshirt": 8.50, "mug": 6.00, "hat": 10.00, "phone_case": 8.00, "sticker": 2.50}[pt]
                markup = 2.5
                retail = round(max(base_cost * markup, {"tshirt": 24.99, "mug": 18.99, "hat": 26.99, "phone_case": 22.99, "sticker": 6.99}[pt]), 2)
                product = Product(
                    design_id=design.id,
                    product_type=pt,
                    printify_base_cost=base_cost,
                    base_markup=markup,
                    trend_adjustment=round(sd["final_score"] / 100 * 0.20 * base_cost * markup, 2),
                    retail_price=retail,
                    floor_price={"tshirt": 24.99, "mug": 18.99, "hat": 26.99, "phone_case": 22.99, "sticker": 6.99}[pt],
                    publish_status="pending",
                )
                db.add(product)

            # Sample marketing assets
            for channel in ("instagram", "tiktok", "pinterest", "email", "blog"):
                asset = MarketingAsset(
                    design_id=design.id,
                    channel=channel,
                    content={"generated": True, "concept": sd["concept_name"]},
                    status="pending",
                )
                db.add(asset)

        db.commit()
        print(f"  Created test batch with {len(sample_designs)} sample designs")
        print("\nSeed complete! Database is ready for mobile app development.")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
