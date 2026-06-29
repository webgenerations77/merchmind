"""Tests for sanitize_copy() — strips AI-tell punctuation from store copy."""
import json
from unittest.mock import patch

from app.services.design import shopify_copy_generator
from app.services.design.shopify_copy_generator import sanitize_copy, generate_shopify_copy


def test_em_dash_with_spaces_becomes_comma():
    assert sanitize_copy("Stick it anywhere — laptops, bottles") == "Stick it anywhere, laptops, bottles"


def test_em_dash_without_spaces_becomes_comma():
    assert sanitize_copy("soft tee—chaotic energy") == "soft tee, chaotic energy"


def test_en_dash_becomes_comma():
    assert sanitize_copy("cozy and warm – all winter") == "cozy and warm, all winter"


def test_double_hyphen_becomes_comma():
    assert sanitize_copy("wait -- what") == "wait, what"


def test_single_hyphen_is_preserved():
    assert sanitize_copy("dog-mom cotton-poly tee") == "dog-mom cotton-poly tee"


def test_curly_double_quotes_become_straight():
    assert sanitize_copy("“Good Boy” club") == '"Good Boy" club'


def test_curly_apostrophe_becomes_straight():
    assert sanitize_copy("you’ll love it") == "you'll love it"


def test_ellipsis_char_becomes_three_dots():
    assert sanitize_copy("wait for it…") == "wait for it..."


def test_space_before_comma_is_removed():
    # em-dash at a clause that already had a comma after shouldn't leave " ,"
    assert sanitize_copy("here — , there") == "here, there"


def test_no_double_comma():
    assert sanitize_copy("one —, two") == "one, two"


def test_collapses_resulting_double_spaces():
    assert sanitize_copy("a  b") == "a b"


def test_trims_whitespace():
    assert sanitize_copy("  hello  ") == "hello"


def test_empty_string_unchanged():
    assert sanitize_copy("") == ""


def test_none_returns_none():
    assert sanitize_copy(None) is None


def test_plain_text_unchanged():
    assert sanitize_copy("A soft cotton tee with a funny dog on it.") == "A soft cotton tee with a funny dog on it."


def test_generate_shopify_copy_sanitizes_model_output():
    payload = json.dumps({
        "shopify_title": "Trash Panda — Energy",
        "shopify_description": "For the chaos goblins — running on spite and coffee.",
        "shopify_tags": ["raccoon", "dog-mom"],
    })
    with patch.object(shopify_copy_generator.claude, "sonnet", return_value=(payload, {})):
        out = generate_shopify_copy("Trash Panda Energy", "trash panda", "illustration", ["tshirt"])
    assert "—" not in out["shopify_title"]
    assert "—" not in out["shopify_description"]
    assert out["shopify_title"] == "Trash Panda, Energy"
    assert out["shopify_description"] == "For the chaos goblins, running on spite and coffee."
    assert "dog-mom" in out["shopify_tags"]  # single hyphen in tags preserved
