from app.config import settings


def test_catalog_tunables_have_defaults():
    assert settings.PRINTIFY_CATALOG_TTL_HOURS == 24
    assert settings.PRINTIFY_MAX_COLORS_PER_PRODUCT == 25
