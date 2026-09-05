from app.services.economic_series import economic_series_info, economic_series_label


def test_economic_series_label_returns_friendly_known_label() -> None:
    assert economic_series_label("UNRATE") == "Unemployment Rate"
    assert economic_series_label("FEDFUNDS") == "Federal Funds Rate"
    assert economic_series_label("MORTGAGE30US") == "30-Year Fixed Mortgage Rate"


def test_economic_series_info_falls_back_to_source_name() -> None:
    info = economic_series_info("CUSTOM_SERIES", "Custom Series Name")

    assert info.series_id == "CUSTOM_SERIES"
    assert info.label == "Custom Series Name"
    assert info.description == "Economic data series."
