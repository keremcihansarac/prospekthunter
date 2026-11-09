# ProspektHunter

Finds the offers you care about in German supermarket flyers, so you can skip the rest.

> **Status:** v0.1. It reads REWE flyer PDFs. More retailers are planned.

## The idea

Weekly flyers are long, and most of their pages are irrelevant to any one person.
ProspektHunter reads them on your own computer, keeps the products that match your
interests, and lists them with their price, package size and exact validity dates.

Interests are product groups rather than single items. The default groups suit a
protein-focused diet. They cover products such as skyr, eggs, chicken breast and lentils,
and they leave out false matches such as *Eierlikör* or *Kontaktlinsen*.

## Getting started

You need [uv](https://docs.astral.sh/uv/) and a flyer PDF downloaded from your retailer.
Keep the retailer's name in the file name, because that is how the tool recognizes it.

```sh
git clone https://github.com/keremcihansarac/prospekthunter.git
cd prospekthunter
uv run prospekthunter report ~/Downloads/rewe-flyer.pdf
```

The output looks like this (example data):

```text
09.11.2026 – 14.11.2026

Dairy
  REWE  Example Skyr Natur               1,29 €  je 450-g-Becher  09.11. – 14.11.

Lean meat
  REWE  Example Chicken Breast           4,99 €  je 400-g-Pckg.   09.11. – 14.11.
```

## Your own product groups

Copy [`categories.yaml`](src/prospekthunter/data/categories.yaml), edit it, and pass it in:

```sh
uv run prospekthunter report rewe-flyer.pdf --categories my-groups.yaml
```

Terms are compared with whole words, ignoring upper and lower case:

| Term | Matches | Does not match |
|---|---|---|
| `eier` | Eier, Bio-Eier | Eierlikör |
| `puten*` | Putenbrust | Computer |
| `"*quark"` | Magerquark | Quarktasche |
| `"*whey*"` | Wheyprotein | |

A product appears once, under the first group that accepts it.

## Sources

| Retailer | Method | State |
|---|---|---|
| REWE | Local import of a flyer PDF you downloaded | Available |
| ALDI SÜD | Local import of a flyer PDF you downloaded | Planned |
| Lidl, Penny, Kaufland | Automatic retrieval, if each retailer's terms allow it | Planned |

Flyer text is not always in reading order, so a product name can occasionally pick up
nearby text, and an offer can be missed. Check the printed flyer before relying on a
price. REWE flyers state only their first day, so the last day is taken to be that
week's Saturday.

## Data and legal note

This repository contains code only. It does not include or publish flyers, offers,
prices or product images, and you run the tool for your own private use. The project
does not bypass bot protection or other access restrictions. It is not affiliated with
any retailer.

## Development

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

## License

[MIT](LICENSE)
