from app.models.product import Product
from app.schemas.product import ProductOut, ProductUpdate


def test_product_model_has_color_columns():
    cols = set(Product.__table__.columns.keys())
    assert "selected_color" in cols
    assert "color_mockups" in cols


def test_product_update_accepts_selected_color():
    u = ProductUpdate(selected_color="heather navy")
    assert u.selected_color == "heather navy"


def test_product_out_exposes_color_fields():
    fields = ProductOut.model_fields
    assert "selected_color" in fields
    assert "color_mockups" in fields
