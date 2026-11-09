import prospekthunter


def test_package_exposes_installed_version() -> None:
    assert prospekthunter.__version__ == "0.0.1"
