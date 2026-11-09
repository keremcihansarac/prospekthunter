from datetime import date
from decimal import Decimal

from prospekthunter.models import Offer
from prospekthunter.sources.rewe import parse_pages


def page(*lines: str) -> str:
    return "\r\n".join(lines)


def parse_one(*lines: str) -> Offer:
    offers = parse_pages([page(*lines)])
    assert len(offers) == 1
    return offers[0]


def test_reads_name_package_and_price() -> None:
    offer = parse_one(
        "Testmarke",
        "Skyr Natur",
        "versch. Sorten,",
        "je 450-g-Becher",
        "(1 kg = 2.87)",
        "Aktion",
        "1.29",
    )

    assert offer.retailer == "REWE"
    assert offer.name == "Testmarke Skyr Natur versch. Sorten"
    assert offer.package == "je 450-g-Becher"
    assert offer.price == Decimal("1.29")


def test_accepts_all_labels_in_any_case() -> None:
    offers = parse_pages(
        [
            page(
                "Produkt A",
                "je 100 g",
                "Knaller",
                "1.00",
                "Produkt B",
                "je 100 g",
                "Tiefpreis",
                "2.00",
                "Produkt C",
                "je 100 g",
                "AKTION",
                "3.00",
            )
        ]
    )

    assert [offer.name for offer in offers] == ["Produkt A", "Produkt B", "Produkt C"]


def test_next_product_can_start_on_the_price_line() -> None:
    offers = parse_pages(
        [
            page(
                "Mini Gurke",
                "je St.",
                "Knaller",
                "0.33 Frisches",
                "Hähnchen-Brustfilet",
                "je 1000-g-Pckg.",
                "Knaller",
                "9.99",
            )
        ]
    )

    assert [(offer.name, offer.price) for offer in offers] == [
        ("Mini Gurke", Decimal("0.33")),
        ("Frisches Hähnchen-Brustfilet", Decimal("9.99")),
    ]


def test_keeps_variants_joined_by_oder() -> None:
    offer = parse_one(
        "Testmarke",
        "Cheddar Scheiben",
        "je 130-g-Pckg.",
        "(1 kg = 12.23)",
        "oder Cheddar",
        "gerieben",
        "je 150-g-Pckg.",
        "(1 kg = 10.60)",
        "Knaller",
        "1.59",
    )

    assert offer.name == "Testmarke Cheddar Scheiben oder Cheddar gerieben"
    assert offer.package == "je 130-g-Pckg. je 150-g-Pckg."


def test_drops_leftovers_of_a_previous_product() -> None:
    offer = parse_one(
        "Fremdmarke",
        "Goldmais",
        "je 300-g-Dose",
        "(1 kg = 3.89)",
        "Testmarke",
        "Cheddar",
        "je 130-g-Pckg.",
        "Knaller",
        "1.59",
    )

    assert offer.name == "Testmarke Cheddar"
    assert offer.package == "je 130-g-Pckg."


def test_removes_leading_oder() -> None:
    offers = parse_pages(
        [
            page(
                "Erstes Produkt",
                "je St.",
                "Knaller",
                "0.99 oder Kidney Bohnen",
                "je 400-g-Dose",
                "Knaller",
                "1.11",
            )
        ]
    )

    assert offers[1].name == "Kidney Bohnen"


def test_ignores_marketing_lines_before_a_product() -> None:
    offer = parse_one(
        "Jetzt zugreifen & sparen:",
        "Heiße Angebote",
        "für kalte Tage!",
        "Testprodukt",
        "je St.",
        "Aktion",
        "1.00",
    )

    assert offer.name == "Testprodukt"


def test_ignores_bonus_deposit_and_single_price_lines() -> None:
    offer = parse_one(
        "0,10€",
        "Bonus",
        "Testbier",
        "Einzelpreis 1.79 €",
        "je 0,5-l-Fl.",
        "(1 l = 1.10)",
        "zzgl. 0.25 Pfand",
        "Aktion",
        "0.99",
    )

    assert offer.name == "Testbier"
    assert offer.package == "je 0,5-l-Fl."


def test_keeps_abbreviations_in_names() -> None:
    offer = parse_one("Testkäse", "50% Fett i.Tr.", "je 100 g", "Aktion", "1.79")

    assert offer.name == "Testkäse 50% Fett i.Tr."


def test_removes_inline_unit_price_from_package() -> None:
    offer = parse_one("Testsnack", "je 4 x 28-g-Pckg. (1 kg = 13.30)", "Aktion", "1.49")

    assert offer.package == "je 4 x 28-g-Pckg."


def test_repairs_control_character_hyphens() -> None:
    offer = parse_one("Schoko\x02Pudding", "je St.", "Aktion", "1.00")

    assert offer.name == "Schoko-Pudding"


def test_joins_compound_word_split_across_lines() -> None:
    offer = parse_one("Frische Puten\x02", "Schnitzel", "je 100 g", "Aktion", "1.59")

    assert offer.name == "Frische Puten-Schnitzel"


def test_joins_single_word_split_across_lines() -> None:
    offer = parse_one("Schmelzkäse\x02", "zubereitung", "je 100 g", "Aktion", "0.99")

    assert offer.name == "Schmelzkäsezubereitung"


def test_package_split_across_lines_stays_in_package() -> None:
    offer = parse_one("Testwasser", "je 1-l-Fl.-", "Kasten", "Aktion", "7.99")

    assert offer.name == "Testwasser"
    assert offer.package == "je 1-l-Fl.-Kasten"


def test_reads_validity_and_ends_on_saturday() -> None:
    offers = parse_pages(
        [
            page("46. Woche 2026. Gültig ab 09.11.2026", "Testprodukt", "je St.", "Aktion", "1.00"),
        ]
    )

    assert offers[0].valid_from == date(2026, 11, 9)
    assert offers[0].valid_until == date(2026, 11, 14)


def test_finds_validity_on_any_page() -> None:
    offers = parse_pages(
        [
            page("Testprodukt", "je St.", "Aktion", "1.00"),
            page("Gültig ab 09.11.2026"),
        ]
    )

    assert offers[0].valid_from == date(2026, 11, 9)


def test_missing_validity_stays_unknown() -> None:
    offer = parse_one("Testprodukt", "je St.", "Aktion", "1.00")

    assert offer.valid_from is None
    assert offer.valid_until is None


def test_label_without_price_is_not_an_offer() -> None:
    assert parse_pages([page("Testprodukt", "Aktion", "gilt nur heute")]) == []


def test_price_without_a_name_is_skipped() -> None:
    assert parse_pages([page("Aktion", "1.00")]) == []
