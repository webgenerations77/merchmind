"""
Seasonal calendar intelligence.
Generates merch signals for upcoming holidays and events within the next 45 days.
"""
import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)

_LOOKAHEAD_DAYS = 45
# Minimum production + shipping lead time. Events closer than this are skipped —
# there's no way to design, produce (Printify), and ship to a customer in time.
_MIN_LEAD_DAYS = 14

# Evergreen merch themes — steady year-round demand, not tied to a date.
# Always available so the seasonal source stays productive in calendar gaps
# (e.g. mid-summer) and so seasonal-only batches always have material.
_EVERGREEN_THEMES: list[tuple[str, list[str]]] = [
    ("Dog Lovers",       ["dog mom", "fur baby", "rescue dog"]),
    ("Cat Lovers",       ["cat mom", "crazy cat lady", "adopt don't shop"]),
    ("Coffee Lovers",    ["but first coffee", "espresso yourself", "caffeine"]),
    ("Plant Parents",    ["plant lady", "crazy plant person", "propagation"]),
    ("Book Lovers",      ["bookworm", "just one more chapter", "bibliophile"]),
    ("Mental Health",    ["self care", "you matter", "be kind to your mind"]),
    ("Fitness",          ["gym rat", "lift heavy", "rest day"]),
    ("Gamers",           ["just one more game", "press start", "loading"]),
    ("Outdoors",         ["adventure awaits", "take a hike", "national park"]),
    ("Sarcasm / Humor",  ["ugh, people", "introvert", "running late"]),
    ("Music Lovers",     ["vinyl", "good vibes", "concert ready"]),
    ("Foodies",          ["taco lover", "pizza is life", "snack queen"]),
]
_EVERGREEN_SCORE = 55  # steady demand, ranks below an imminent timely holiday

# Static calendar — (month, day, name, keywords)
_EVENTS: list[tuple[int, int, str, list[str]]] = [
    (1, 1,  "New Year's Day",          ["new year", "fresh start", "resolution"]),
    (1, 15, "Martin Luther King Jr. Day", ["MLK", "dream", "equality", "justice"]),
    (2, 2,  "Groundhog Day",           ["groundhog", "shadow", "spring early"]),
    (2, 14, "Valentine's Day",         ["love", "heart", "valentine", "couple"]),
    (3, 17, "St. Patrick's Day",       ["lucky", "clover", "Irish", "green"]),
    (4, 1,  "April Fools' Day",        ["prank", "fooled", "joke"]),
    (4, 22, "Earth Day",               ["earth day", "eco", "planet", "green"]),
    (5, 4,  "Star Wars Day",           ["may the 4th", "star wars", "jedi", "force"]),
    (5, 5,  "Cinco de Mayo",           ["cinco de mayo", "fiesta", "Mexican"]),
    (5, 12, "Mother's Day",            ["mom", "mother", "mama", "mommy"]),  # 2nd Sunday May
    (6, 15, "Father's Day",            ["dad", "father", "papa", "daddy"]),  # 3rd Sunday June
    (6, 19, "Juneteenth",              ["juneteenth", "freedom", "liberation"]),
    (7, 4,  "Independence Day",        ["4th of July", "USA", "freedom", "patriot"]),
    (8, 26, "National Dog Day",        ["dog day", "puppy", "dog mom", "fur baby"]),
    (9, 5,  "Labor Day",               ["labor day", "workers", "weekend"]),
    (10, 4, "World Animal Day",        ["animal day", "pets", "wildlife"]),
    (10, 10, "World Mental Health Day", ["mental health", "self care", "awareness"]),
    (10, 31, "Halloween",              ["halloween", "spooky", "witch", "ghost", "costume"]),
    (11, 1,  "Day of the Dead",        ["day of the dead", "skull", "marigold"]),
    (11, 11, "Veterans Day",           ["veterans day", "military", "hero", "freedom"]),
    (11, 27, "Thanksgiving",           ["thanksgiving", "grateful", "turkey", "family"]),  # approx
    (12, 1,  "Ugly Sweater Season",    ["ugly sweater", "christmas sweater", "holiday"]),
    (12, 21, "Winter Solstice",        ["winter solstice", "cozy", "hibernate"]),
    (12, 25, "Christmas",              ["christmas", "santa", "holiday", "merry"]),
    (12, 26, "Kwanzaa",               ["kwanzaa", "unity", "culture", "heritage"]),
    (12, 31, "New Year's Eve",        ["new year's eve", "countdown", "cheers"]),
]


def _days_until(month: int, day: int, from_date: date) -> int:
    target = date(from_date.year, month, day)
    if target < from_date:
        target = date(from_date.year + 1, month, day)
    return (target - from_date).days


def get_upcoming_events(from_date: date = None) -> list[dict]:
    """
    Return seasonal signals for events within the next 45 days.
    Weighted by proximity: closer events get higher scores.
    """
    from_date = from_date or date.today()
    results = []
    skipped_close = 0

    for month, day, name, keywords in _EVENTS:
        try:
            days_until = _days_until(month, day, from_date)
        except ValueError:
            continue  # invalid date like Feb 29

        if days_until > _LOOKAHEAD_DAYS:
            continue

        # Skip events too close to design, produce, and ship in time.
        if days_until < _MIN_LEAD_DAYS:
            skipped_close += 1
            continue

        # Score inversely proportional to days remaining; floor at 30
        proximity_score = max(30, 100 - int(days_until * 1.5))

        for kw in keywords:
            results.append({
                "raw_signal": f"{name}: {kw}",
                "source": "seasonal",
                "source_metadata": {
                    "event": name,
                    "keyword": kw,
                    "days_until": days_until,
                    "proximity_score": proximity_score,
                },
            })

    # Evergreen themes — always available, no date gating.
    for theme, keywords in _EVERGREEN_THEMES:
        for kw in keywords:
            results.append({
                "raw_signal": f"{theme}: {kw}",
                "source": "seasonal",
                "source_metadata": {
                    "event": theme,
                    "keyword": kw,
                    "evergreen": True,
                    "proximity_score": _EVERGREEN_SCORE,
                },
            })

    logger.info(
        f"Seasonal calendar: {len(results)} signals "
        f"({len(_EVERGREEN_THEMES)} evergreen themes, "
        f"{skipped_close} event(s) skipped for <{_MIN_LEAD_DAYS}d lead time)"
    )
    return results
