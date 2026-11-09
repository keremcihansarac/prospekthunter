"""Data structures shared by every offer source."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Offer:
    """A single product offer, independent of the flyer it came from.

    Either date may be ``None`` because flyers do not always state them. Some say only
    "ab Mo. 9.11." and leave the end open.
    """

    retailer: str
    name: str
    price: Decimal
    valid_from: date | None = None
    valid_until: date | None = None
    package: str | None = None
    requires_app: bool = False

    def __post_init__(self) -> None:
        if not self.retailer.strip():
            raise ValueError("retailer must not be blank")
        if not self.name.strip():
            raise ValueError("name must not be blank")
        if self.price <= 0:
            raise ValueError(f"price must be positive, got {self.price}")
        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_until < self.valid_from
        ):
            raise ValueError(f"offer ends {self.valid_until} before it starts {self.valid_from}")
