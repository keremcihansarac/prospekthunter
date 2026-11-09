import re

import prospekthunter


def test_package_exposes_a_version_number() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", prospekthunter.__version__)
