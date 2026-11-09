from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from prospekthunter.models import Offer
from prospekthunter.sources import flyers
from prospekthunter.sources.aldi import parse_pages

TODAY = date(2026, 11, 10)


def page(*lines: str) -> str:
    return "\r\n".join(lines)


def parse_one(*lines: str) -> Offer:
    offers = parse_pages([page(*lines)], TODAY)
    assert len(offers) == 1
    return offers[0]


def test_reads_brand_name_package_and_split_price() -> None:
    offer = parse_one(
        "MEINE MARKE",
        "Puten-Ministeaks",
        "400-g-Packung; kg-Preis 11.48",
        "4.",
        "59*",
    )

    assert offer.retailer == "ALDI SÜD"
    assert offer.name == "MEINE MARKE Puten-Ministeaks"
    assert offer.package == "400-g-Packung"
    assert offer.price == Decimal("4.59")


def test_reads_price_without_asterisk_and_price_on_one_line() -> None:
    offers = parse_pages(
        [
            page(
                "Produkt A",
                "100-g-Packung; kg-Preis 23.90",
                "2.",
                "39",
                "Produkt B",
                "500-g-Packung, kg-Preis 37.98",
                "18.99*",
            )
        ],
        TODAY,
    )

    assert [(offer.name, offer.price) for offer in offers] == [
        ("Produkt A", Decimal("2.39")),
        ("Produkt B", Decimal("18.99")),
    ]


def test_old_price_and_discount_do_not_leak_into_the_next_name() -> None:
    offers = parse_pages(
        [
            page(
                "Produkt A",
                "1-kg-Packung",
                "4.",
                "39*",
                "5.59",
                "XXL",
                "-21%",
                "Aktion",
                "ab 1.09",
                "Produkt B",
                "1-kg-Packung",
                "3.",
                "59*",
            )
        ],
        TODAY,
    )

    assert [offer.name for offer in offers] == ["Produkt A", "Produkt B"]


def test_next_product_can_start_on_the_cents_line() -> None:
    offers = parse_pages(
        [
            page(
                "Produkt A",
                "1-kg-Packung",
                "1.",
                "99* MARKE",
                "Produkt B",
                "1-kg-Packung",
                "2.",
                "49*",
            )
        ],
        TODAY,
    )

    assert offers[1].name == "MARKE Produkt B"


def test_skips_section_label_between_details_and_price() -> None:
    offer = parse_one("Testquark", "250-g-Becher; kg-Preis 2.00", "KÜHLUNG", "0.", "50")

    assert offer.name == "Testquark"
    assert offer.price == Decimal("0.50")


def test_details_of_another_product_start_the_block_again() -> None:
    offer = parse_one(
        "Fremdprodukt",
        "2-kg-Tasche; kg-Preis 1.00",
        "Mango",
        "Klasse: I; Stück",
        "1.",
        "99*",
    )

    assert offer.name == "Mango"
    assert offer.package == "Stück"


@pytest.mark.parametrize(
    "line",
    [
        "• Futter aus ökologischem Anbau",
        "Mehr auf haltungsform.de/kriterien",
        "Von der Geburt bis zur Verarbeitung und noch viel weiter hinaus",
        "Unser Versprechen!",
    ],
)
def test_advertising_text_stays_out_of_the_name(line: str) -> None:
    offer = parse_one(line, "MARKE", "Lachsfilet", "300-g-Packung; kg-Preis 14.97", "4.", "49*")

    assert offer.name == "MARKE Lachsfilet"


def test_joins_name_split_across_lines() -> None:
    offer = parse_one("Lachs\xad\x02", "forellen", "300-g-Packung; kg-Preis 10.00", "3.", "00*")

    assert offer.name == "Lachsforellen"


@pytest.mark.parametrize("prefix", ["79* ", "ab Mo. 9.11. "])
def test_removes_price_and_date_fragments_from_the_name(prefix: str) -> None:
    offer = parse_one(f"{prefix}MARKE Testkäse", "150-g-Packung; kg-Preis 7.93", "1.", "19*")

    assert offer.name == "MARKE Testkäse"


def test_heading_without_details_is_not_an_offer() -> None:
    assert parse_pages([page("TIEFPREIS-HIGHLIGHTS", "3.", "89*")], TODAY) == []


def test_ignores_price_with_no_name() -> None:
    assert parse_pages([page("0.", "75*")], TODAY) == []


def test_drops_offer_whose_price_contradicts_its_details() -> None:
    lines = ("Speisezwiebeln", "1,5-kg-Netz; kg-Preis 0.93", "0.", "59*")

    assert parse_pages([page(*lines)], TODAY) == []


@pytest.mark.parametrize(
    "detail",
    [
        "200-g-Packung; Abtropfgewicht 125 g; kg-Preis 10.32 / Abtropfgewicht",
        "je 160- bzw. 175-g-Packung; kg-Preis 9.97 bzw. 9.11",
        "Versch. Gewichte, z. B. 594 g; kg-Preis 2.17",
    ],
)
def test_keeps_offers_that_cannot_be_checked(detail: str) -> None:
    offer = parse_one("Testprodukt", detail, "1.", "29")

    assert offer.price == Decimal("1.29")


def test_checks_multipacks_by_total_size() -> None:
    offer = parse_one("Testriegel", "je 5 x 45-g-Packung; kg-Preis 8.84", "1.", "99*")

    assert offer.price == Decimal("1.99")


def validity(*labels: str) -> tuple[date | None, date | None]:
    offer = parse_one(*labels, "Testprodukt", "1-kg-Packung", "1.", "00*")
    return offer.valid_from, offer.valid_until


def test_reads_date_range() -> None:
    assert validity("Mo. 9.11. – Sa. 14.11.") == (date(2026, 11, 9), date(2026, 11, 14))


def test_reads_open_ended_date() -> None:
    assert validity("ab Do. 12.11.") == (date(2026, 11, 12), None)


def test_several_labels_leave_dates_unknown() -> None:
    assert validity("ab Mo. 16.11. ab Do. 19.11.") == (None, None)


def test_page_without_label_leaves_dates_unknown() -> None:
    assert validity() == (None, None)


def test_ignores_impossible_placeholder_dates() -> None:
    assert validity("ab Mo. 0.0.", "ab Mo. 9.11.") == (date(2026, 11, 9), None)


def test_year_rolls_over_near_new_year() -> None:
    lines = ("ab Mo. 4.1.", "Testprodukt", "1-kg-Packung", "1.", "00*")

    offers = parse_pages([page(*lines)], date(2026, 12, 28))

    assert offers[0].valid_from == date(2027, 1, 4)


@pytest.mark.parametrize(
    "name",
    ["ALDI SÜD Prospekt.pdf", "ALDI SÜD Prospekt.pdf", "aldi-sued-prospekt.pdf"],
)
def test_recognizes_aldi_sued_file_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    flyer = tmp_path / name
    flyer.write_bytes(b"%PDF-1.4")
    expected = [Offer(retailer="ALDI SÜD", name="Testprodukt", price=Decimal("1.00"))]
    monkeypatch.setattr(flyers, "read_aldi_pdf", lambda path: expected)

    assert flyers.read_flyer(flyer) == expected


def test_aldi_nord_is_not_read_as_aldi_sued(tmp_path: Path) -> None:
    flyer = tmp_path / "ALDI Nord Prospekt.pdf"
    flyer.write_bytes(b"%PDF-1.4")

    with pytest.raises(ValueError, match="unsupported flyer"):
        flyers.read_flyer(flyer)
