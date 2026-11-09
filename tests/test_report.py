from dataclasses import replace
from datetime import date
from decimal import Decimal

from prospekthunter.models import Offer
from prospekthunter.report import format_report

OFFER = Offer(
    retailer="REWE",
    name="Test Skyr",
    price=Decimal("1.29"),
    valid_from=date(2026, 11, 9),
    valid_until=date(2026, 11, 14),
    package="je 450-g-Becher",
)


def test_reports_no_matches() -> None:
    assert format_report({}) == "No matching offers found."


def test_shows_period_group_and_exact_dates() -> None:
    assert format_report({"Dairy": [OFFER]}).splitlines() == [
        "09.11.2026 – 14.11.2026",
        "",
        "Dairy",
        "  REWE  Test Skyr    1,29 €  je 450-g-Becher  09.11. – 14.11.",
    ]


def test_period_spans_all_offers() -> None:
    later = replace(OFFER, valid_from=date(2026, 11, 16), valid_until=date(2026, 11, 21))

    assert format_report({"Dairy": [OFFER, later]}).startswith("09.11.2026 – 21.11.2026")


def test_columns_align_across_groups() -> None:
    longer = replace(OFFER, retailer="ALDI SÜD", name="Sehr langer Testname")

    rows = [
        line
        for line in format_report({"Dairy": [OFFER], "Eggs": [longer]}).splitlines()
        if line.startswith("  ")
    ]

    assert rows[0].index("1,29 €") == rows[1].index("1,29 €")


def test_shortens_long_names() -> None:
    report = format_report({"Dairy": [replace(OFFER, name="x" * 80)]})

    assert "x" * 59 + "…" in report
    assert "x" * 60 not in report


def test_marks_app_only_prices() -> None:
    report = format_report({"Dairy": [replace(OFFER, requires_app=True)]})

    assert report.endswith("(App)")


def test_handles_missing_package() -> None:
    report = format_report({"Dairy": [replace(OFFER, package=None)]})

    assert report.splitlines()[-1] == "  REWE  Test Skyr    1,29 €    09.11. – 14.11."


def test_single_day_offer_shows_one_date() -> None:
    offer = replace(OFFER, valid_until=OFFER.valid_from)

    assert format_report({"Dairy": [offer]}).endswith("  09.11.")


def test_open_ended_offer() -> None:
    report = format_report({"Dairy": [replace(OFFER, valid_until=None)]})

    assert report.startswith("from 09.11.2026")
    assert report.endswith("from 09.11.")


def test_offer_with_only_an_end_date() -> None:
    report = format_report({"Dairy": [replace(OFFER, valid_from=None)]})

    assert report.startswith("until 14.11.2026")
    assert report.endswith("until 14.11.")


def test_unknown_dates_are_stated_without_a_period() -> None:
    report = format_report({"Dairy": [replace(OFFER, valid_from=None, valid_until=None)]})

    assert report.startswith("Dairy")
    assert report.endswith("date unknown")


def test_skips_empty_groups() -> None:
    assert "Eggs" not in format_report({"Dairy": [OFFER], "Eggs": []})
