"""Loading of the product groups a user wants to see."""

from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

import yaml

_ALLOWED_KEYS = {"name", "include", "exclude"}


@dataclass(frozen=True, slots=True)
class Category:
    """A named product group described by the terms that select and reject products."""

    name: str
    include: tuple[str, ...]
    exclude: tuple[str, ...] = ()


def load_categories(path: Path | None = None) -> tuple[Category, ...]:
    """Read categories from ``path``, or the packaged defaults when no path is given."""
    if path is None:
        resource = files("prospekthunter").joinpath("data/categories.yaml")
        text = resource.read_text(encoding="utf-8")
    else:
        text = path.read_text(encoding="utf-8")

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise ValueError(f"categories file is not valid YAML: {error}") from error

    entries = data.get("categories") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not entries:
        raise ValueError("categories file must contain a non-empty 'categories' list")

    categories = tuple(_parse_category(entry) for entry in entries)
    names = [category.name for category in categories]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ValueError(f"duplicate category names: {', '.join(duplicates)}")
    return categories


def _parse_category(entry: object) -> Category:
    if not isinstance(entry, dict):
        raise ValueError(f"category must be a mapping, got {entry!r}")

    name = entry.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"category needs a non-blank 'name', got {entry!r}")

    unknown = set(entry) - _ALLOWED_KEYS
    if unknown:
        keys = ", ".join(sorted(str(key) for key in unknown))
        raise ValueError(f"category {name!r} has unknown keys: {keys}")

    include = _parse_terms(entry.get("include"), "include", name)
    if not include:
        raise ValueError(f"category {name!r} needs at least one 'include' term")
    exclude = _parse_terms(entry.get("exclude", []), "exclude", name)
    return Category(name=name, include=include, exclude=exclude)


def _parse_terms(value: object, field: str, category: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"category {category!r}: '{field}' must be a list")
    for term in value:
        if not isinstance(term, str) or not term.strip():
            raise ValueError(f"category {category!r}: invalid '{field}' term {term!r}")
    return tuple(value)
