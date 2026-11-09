from dataclasses import FrozenInstanceError, replace
from datetime import date
from decimal import Decimal

import pytest

from prospekthunter.models import Offer

OFFER = Offer(
    retailer="REWE",
    name="Test Skyr Natur",
    price=Decimal("1.29"),
    valid_from=date(2026, 11, 9),
    valid_until=date(2026, 11, 14),
    package="450-g-Becher",
)


def test_offer_keeps_exact_price() -> None:
    assert OFFER.price == Decimal("1.29")


def test_optional_fields_have_safe_defaults() -> None:
    offer = Offer(retailer="ALDI SÜD", name="Test Eier", price=Decimal("1.99"))

    assert offer.valid_from is None
    assert offer.valid_until is None
    assert offer.package is None
    assert offer.requires_app is False


def test_offer_allows_open_ended_validity() -> None:
    offer = replace(OFFER, valid_until=None)

    assert offer.valid_from == date(2026, 11, 9)
    assert offer.valid_until is None


def test_offer_allows_single_day_validity() -> None:
    offer = replace(OFFER, valid_until=OFFER.valid_from)

    assert offer.valid_until == offer.valid_from


def test_offer_is_immutable() -> None:
    with pytest.raises(FrozenInstanceError):
        OFFER.price = Decimal("0.99")  # type: ignore[misc]


@pytest.mark.parametrize("blank", ["", "   ", "\n"])
def test_rejects_blank_name(blank: str) -> None:
    with pytest.raises(ValueError, match="name"):
        replace(OFFER, name=blank)


@pytest.mark.parametrize("blank", ["", "   "])
def test_rejects_blank_retailer(blank: str) -> None:
    with pytest.raises(ValueError, match="retailer"):
        replace(OFFER, retailer=blank)


@pytest.mark.parametrize("price", ["0", "0.00", "-1.29"])
def test_rejects_non_positive_price(price: str) -> None:
    with pytest.raises(ValueError, match="price"):
        replace(OFFER, price=Decimal(price))


def test_rejects_end_before_start() -> None:
    with pytest.raises(ValueError, match="before it starts"):
        replace(OFFER, valid_until=date(2026, 11, 8))
