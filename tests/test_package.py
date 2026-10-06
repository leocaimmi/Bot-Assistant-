import asistente


def test_package_exposes_version() -> None:
    assert asistente.__version__ == "0.1.0"
