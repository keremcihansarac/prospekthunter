from pathlib import Path

import pytest

from prospekthunter.categories import Category, load_categories


def write_categories(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "categories.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def test_default_categories_cover_the_fit_groups() -> None:
    names = [category.name for category in load_categories()]

    assert names == [
        "Protein products",
        "Dairy",
        "Eggs",
        "Lean meat",
        "Fish and seafood",
        "Plant protein",
        "Fit staples",
    ]


def test_default_terms_keep_leading_wildcards() -> None:
    dairy = next(category for category in load_categories() if category.name == "Dairy")

    assert "*skyr*" in dairy.include


def test_loads_custom_file(tmp_path: Path) -> None:
    path = write_categories(
        tmp_path,
        """
categories:
  - name: Snacks
    include: [nüsse, "*riegel"]
    exclude: [schoko*]
""",
    )

    assert load_categories(path) == (
        Category(name="Snacks", include=("nüsse", "*riegel"), exclude=("schoko*",)),
    )


def test_exclude_is_optional(tmp_path: Path) -> None:
    path = write_categories(tmp_path, "categories: [{name: Eggs, include: [eier]}]")

    assert load_categories(path)[0].exclude == ()


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("categories: [", "not valid YAML"),
        ("just text", "non-empty 'categories' list"),
        ("categories: []", "non-empty 'categories' list"),
        ("categories: [plain]", "must be a mapping"),
        ("categories: [{include: [eier]}]", "non-blank 'name'"),
        ("categories: [{name: Eggs}]", "'include' must be a list"),
        ("categories: [{name: Eggs, include: []}]", "at least one 'include'"),
        ("categories: [{name: Eggs, include: [no]}]", "invalid 'include' term"),
        ("categories: [{name: Eggs, include: [eier], exclude: schoko}]", "'exclude' must be"),
        ("categories: [{name: Eggs, include: [eier], exlude: [schoko]}]", "unknown keys: exlude"),
        (
            "categories: [{name: Eggs, include: [eier]}, {name: Eggs, include: [ei]}]",
            "duplicate category names: Eggs",
        ),
    ],
)
def test_rejects_invalid_files(tmp_path: Path, content: str, message: str) -> None:
    path = write_categories(tmp_path, content)

    with pytest.raises(ValueError, match=message):
        load_categories(path)
