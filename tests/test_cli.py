from decimal import Decimal
from pathlib import Path

import pytest

from prospekthunter import cli
from prospekthunter.models import Offer
from prospekthunter.sources.flyers import read_flyer


def fake_reader(path: Path) -> list[Offer]:
    return [
        Offer(retailer="REWE", name="Skyr Natur", price=Decimal("1.29")),
        Offer(retailer="REWE", name="Milchschokolade", price=Decimal("0.99")),
    ]


def test_report_prints_only_matching_offers(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "read_flyer", fake_reader)

    assert cli.main(["report", "rewe.pdf"]) == 0

    output = capsys.readouterr().out
    assert "Skyr Natur" in output
    assert "Milchschokolade" not in output


def test_report_uses_custom_categories(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.setattr(cli, "read_flyer", fake_reader)
    categories = tmp_path / "mine.yaml"
    categories.write_text(
        "categories: [{name: Treats, include: [milchschokolade]}]", encoding="utf-8"
    )

    assert cli.main(["report", "rewe.pdf", "--categories", str(categories)]) == 0

    output = capsys.readouterr().out
    assert "Treats" in output
    assert "Skyr Natur" not in output


def test_missing_flyer_is_a_clean_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["report", str(tmp_path / "rewe.pdf")]) == 1

    captured = capsys.readouterr()
    assert "flyer not found" in captured.err
    assert captured.out == ""


def test_unsupported_retailer_is_a_clean_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    flyer = tmp_path / "other.pdf"
    flyer.write_bytes(b"%PDF-1.4")

    assert cli.main(["report", str(flyer)]) == 1

    assert "unsupported flyer: other.pdf" in capsys.readouterr().err


def test_corrupt_pdf_is_a_clean_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    flyer = tmp_path / "rewe.pdf"
    flyer.write_bytes(b"not a pdf")

    assert cli.main(["report", str(flyer)]) == 1

    assert "could not read PDF rewe.pdf" in capsys.readouterr().err


def test_recognizes_rewe_in_any_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    flyer = tmp_path / "REWE Markt GmbH - wk46.pdf"
    flyer.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr("prospekthunter.sources.flyers.read_rewe_pdf", fake_reader)

    assert len(read_flyer(flyer)) == 2
