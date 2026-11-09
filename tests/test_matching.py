from decimal import Decimal

import pytest

from prospekthunter.categories import Category, load_categories
from prospekthunter.matching import CategoryMatcher, normalize
from prospekthunter.models import Offer

MATCHER = CategoryMatcher(load_categories())


def category_name(text: str) -> str | None:
    category = MATCHER.match(text)
    return category.name if category is not None else None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("High Protein Wasser", "Protein products"),
        ("Proteinwraps", "Protein products"),
        ("Proteinmilch Schoko", "Protein products"),
        ("Whey Pulver", "Protein products"),
        ("Eiweißbrot", "Protein products"),
        ("Skyr Natur", "Dairy"),
        ("Vanille-Skyr", "Dairy"),
        ("Magerquark", "Dairy"),
        ("Körniger Frischkäse", "Dairy"),
        ("Körniger Bio-Frischkäse", "Dairy"),
        ("Griechischer Joghurt", "Dairy"),
        ("Frische Eier 10 Stück", "Eggs"),
        ("Bio-Eier", "Eggs"),
        ("Hähnchen-Brustfilet", "Lean meat"),
        ("Hähnchenbrust", "Lean meat"),
        ("Puten-Schnitzel", "Lean meat"),
        ("Rinder-Hackfleisch", "Lean meat"),
        ("Bio-Hackfleisch vom Rind", "Lean meat"),
        ("Schweine-Filet- Medaillons", "Lean meat"),
        ("Thunfisch in eigenem Saft", "Fish and seafood"),
        ("Räucherlachs", "Fish and seafood"),
        ("Rote Linsen", "Plant protein"),
        ("Kidneybohnen", "Plant protein"),
        ("Sojabohnenkerne", "Plant protein"),
        ("Kernige Haferflocken", "Fit staples"),
        ("Vollkornbrot", "Fit staples"),
        ("Basmati Reis", "Fit staples"),
    ],
)
def test_finds_wanted_products(text: str, expected: str) -> None:
    assert category_name(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "Eierlikör",
        "Eier-Teigware",
        "Schoko-Eier",
        "Feier-Set",
        "Kontaktlinsen",
        "Computerspiel",
        "Milchschokolade",
        "Reiseführer",
        "Preis der Woche",
        "Kaffeebohnen",
        "Ganze Bohnen Kaffee",
        "Lachsschinken",
        "Flachsöl",
        "Hähnchen-Nuggets",
        "Puten-Salami",
        "Quarktasche",
        "Schokoquarkcreme",
        "Reis-Waffeln",
        "Vollkorn-Kekse",
        "Fix für Hähnchen Geschnetzeltes",
        "Hähnchen Sandwich",
        "Räucherlachs Sandwich",
    ],
)
def test_ignores_lookalike_products(text: str) -> None:
    assert category_name(text) is None


def test_exclusion_from_one_group_allows_a_later_group() -> None:
    assert category_name("Heringsfilet Eier/Senf") == "Fish and seafood"


def test_first_matching_group_wins() -> None:
    assert category_name("High Protein Hähnchen mit Reis") == "Protein products"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("HÄHNCHEN-KEULE", "Lean meat"),
        ("Hähnchen", "Lean meat"),
        ("Thunﬁsch", "Fish and seafood"),
        ("Eiweiss Riegel", "Protein products"),
        ("Bio‑Eier", "Eggs"),
        ("Sk­yr", "Dairy"),
        ("K-WERTSCHÄTZE Hähnchen-Keule", "Lean meat"),
        ("Hähnchen- Geschnetzeltes", "Lean meat"),
        ("Hüttenkä- se", "Dairy"),
        ("Körniger\nFrischkäse", "Dairy"),
    ],
)
def test_handles_pdf_text_quirks(text: str, expected: str) -> None:
    assert category_name(text) == expected


def test_normalize_collapses_case_space_and_sharp_s() -> None:
    assert normalize("  Weiße\n  BOHNEN ") == "weisse bohnen"


@pytest.mark.parametrize(
    ("term", "text", "expected"),
    [
        ("eier", "Eier", True),
        ("eier", "Eierlikör", False),
        ("puten*", "Putenbrust", True),
        ("puten*", "Computer", False),
        ("*quark", "Magerquark", True),
        ("*quark", "Quarktasche", False),
        ("*whey*", "Wheyprotein", True),
        ("körniger frischkäse", "Körniger-Frischkäse", True),
        ("körnig* frischkäse", "Körnige Frischkäse", True),
        ("a.b", "axb", False),
    ],
)
def test_term_syntax(term: str, text: str, expected: bool) -> None:
    matcher = CategoryMatcher([Category(name="Test", include=(term,))])

    assert (matcher.match(text) is not None) is expected


@pytest.mark.parametrize("term", ["a*b", "*", "---"])
def test_rejects_invalid_terms(term: str) -> None:
    with pytest.raises(ValueError, match="invalid term"):
        CategoryMatcher([Category(name="Test", include=(term,))])


def make_offer(name: str) -> Offer:
    return Offer(retailer="REWE", name=name, price=Decimal("1.00"))


def test_group_offers_uses_category_order_and_drops_the_rest() -> None:
    eggs = make_offer("Bio-Eier")
    skyr = make_offer("Skyr Natur")
    candy = make_offer("Milchschokolade")

    assert MATCHER.group_offers([eggs, candy, skyr]) == {"Dairy": [skyr], "Eggs": [eggs]}


def test_group_offers_omits_empty_groups() -> None:
    assert MATCHER.group_offers([]) == {}
