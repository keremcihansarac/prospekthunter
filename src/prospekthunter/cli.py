"""Command line interface."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from prospekthunter import __version__
from prospekthunter.categories import load_categories
from prospekthunter.matching import CategoryMatcher
from prospekthunter.report import format_report
from prospekthunter.sources.flyers import read_flyer


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prospekthunter",
        description="Find the offers you care about in German supermarket flyers.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    report = commands.add_parser("report", help="list matching offers from flyer PDFs")
    report.add_argument("flyers", nargs="+", type=Path, metavar="FLYER", help="flyer PDF to read")
    report.add_argument(
        "--categories",
        type=Path,
        metavar="FILE",
        help="YAML file with your own product groups",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        matcher = CategoryMatcher(load_categories(args.categories))
        offers = [offer for path in args.flyers for offer in read_flyer(path)]
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(format_report(matcher.group_offers(offers)))
    return 0
