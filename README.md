# ProspektHunter

Finds the offers you care about in German supermarket flyers, so you can skip the rest.

> **Status:** early development. Nothing is usable yet.

## The idea

Weekly flyers are long, and most of their pages are irrelevant to any one person.
ProspektHunter reads them on your own computer, keeps the products that match your
interests, and lists them with their price and exact validity dates.

Interests are product groups rather than single items. A "protein" group, for example,
covers skyr, eggs, chicken breast and similar products, and it leaves out false matches
such as *Eierlikör*.

## Planned sources

| Retailer | Method |
|---|---|
| REWE | Local import of a flyer PDF you downloaded |
| ALDI SÜD | Local import of a flyer PDF you downloaded |
| Lidl, Penny, Kaufland | Automatic retrieval, if each retailer's terms allow it |

## Data and legal note

This repository contains code only. It does not include or publish flyers, offers,
prices or product images, and you run the tool for your own private use. The project
does not bypass bot protection or other access restrictions. It is not affiliated with
any retailer.

## License

[MIT](LICENSE)
