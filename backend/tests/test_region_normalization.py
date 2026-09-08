from app.services.region_normalization import expand_regions, infer_regions_from_text, region_match_values


def test_infer_regions_from_state_abbreviation() -> None:
    regions = infer_regions_from_text("What is happening with housing in AZ?")

    assert "AZ" in regions
    assert "Arizona" in regions


def test_infer_regions_from_state_name() -> None:
    regions = infer_regions_from_text("How is Texas housing trending?")

    assert "TX" in regions
    assert "Texas" in regions


def test_infer_regions_does_not_treat_lowercase_words_as_state_codes() -> None:
    regions = infer_regions_from_text("What is happening in world markets today?")

    assert "IN" not in regions
    assert "Indiana" not in regions


def test_infer_regions_from_metro_phrase() -> None:
    regions = infer_regions_from_text("Is Phoenix housing cooling?")

    assert "Phoenix-Mesa-Chandler, AZ" in regions
    assert "AZ" in regions
    assert "Arizona" in regions


def test_expand_regions_adds_national_context_for_local_region() -> None:
    regions = expand_regions(["Phoenix"])

    assert "Phoenix-Mesa-Chandler, AZ" in regions
    assert "Arizona" in regions
    assert "United States" in regions


def test_region_match_values_treats_state_code_and_name_as_same() -> None:
    assert "arizona" in region_match_values("AZ")
    assert "az" in region_match_values("Arizona")
