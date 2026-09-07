from __future__ import annotations

import re


US_STATE_NAMES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "DC": "District of Columbia",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}


STATE_ABBREVIATIONS_BY_NAME = {name.lower(): code for code, name in US_STATE_NAMES.items()}


METRO_ALIASES = {
    "atlanta": "Atlanta-Sandy Springs-Roswell, GA",
    "austin": "Austin-Round Rock-Georgetown, TX",
    "boston": "Boston-Cambridge-Newton, MA-NH",
    "charlotte": "Charlotte-Concord-Gastonia, NC-SC",
    "chicago": "Chicago-Naperville-Elgin, IL-IN-WI",
    "dallas": "Dallas-Fort Worth-Arlington, TX",
    "denver": "Denver-Aurora-Lakewood, CO",
    "houston": "Houston-The Woodlands-Sugar Land, TX",
    "las vegas": "Las Vegas-Henderson-Paradise, NV",
    "los angeles": "Los Angeles-Long Beach-Anaheim, CA",
    "miami": "Miami-Fort Lauderdale-West Palm Beach, FL",
    "new york": "New York-Newark-Jersey City, NY-NJ-PA",
    "orlando": "Orlando-Kissimmee-Sanford, FL",
    "phoenix": "Phoenix-Mesa-Chandler, AZ",
    "portland": "Portland-Vancouver-Hillsboro, OR-WA",
    "raleigh": "Raleigh-Cary, NC",
    "san antonio": "San Antonio-New Braunfels, TX",
    "san diego": "San Diego-Chula Vista-Carlsbad, CA",
    "san francisco": "San Francisco-Oakland-Berkeley, CA",
    "seattle": "Seattle-Tacoma-Bellevue, WA",
    "tampa": "Tampa-St. Petersburg-Clearwater, FL",
    "washington dc": "Washington-Arlington-Alexandria, DC-VA-MD-WV",
    "washington, dc": "Washington-Arlington-Alexandria, DC-VA-MD-WV",
}


NATIONAL_REGION_ALIASES = ("US", "USA", "United States", "US Market")


def infer_regions_from_text(text: str) -> list[str]:
    normalized = normalize_region_value(text)
    regions: list[str] = []

    for alias, metro in METRO_ALIASES.items():
        if alias in normalized:
            regions.append(metro)
            regions.extend(states_from_metro_name(metro))

    for code, name in US_STATE_NAMES.items():
        if re.search(rf"\b{re.escape(code.lower())}\b", normalized) or name.lower() in normalized:
            regions.extend([code, name])

    if any(term in normalized for term in ("united states", " u s ", " usa ", "national", "us market")):
        regions.extend(NATIONAL_REGION_ALIASES)

    return unique_regions(regions)


def expand_regions(regions: list[str]) -> list[str]:
    expanded: list[str] = []
    for region in regions:
        expanded.append(region)
        normalized = normalize_region_value(region)
        if normalized in STATE_ABBREVIATIONS_BY_NAME:
            code = STATE_ABBREVIATIONS_BY_NAME[normalized]
            expanded.extend([code, US_STATE_NAMES[code]])
        if normalized.upper() in US_STATE_NAMES:
            code = normalized.upper()
            expanded.extend([code, US_STATE_NAMES[code]])
        if normalized in METRO_ALIASES:
            metro = METRO_ALIASES[normalized]
            expanded.append(metro)
            expanded.extend(states_from_metro_name(metro))
        if normalized in {"us", "usa", "u s", "united states", "national", "us market"}:
            expanded.extend(NATIONAL_REGION_ALIASES)

    if expanded and not only_national_regions(expanded):
        expanded.extend(NATIONAL_REGION_ALIASES)

    return unique_regions(expanded)


def region_match_values(region: str | None) -> set[str]:
    if not region:
        return set()
    return {normalize_region_value(value) for value in expand_regions([region])}


def states_from_metro_name(metro: str) -> list[str]:
    if "," not in metro:
        return []
    suffix = metro.rsplit(",", 1)[1]
    states = [part.strip().upper() for part in re.split(r"[-/]", suffix) if part.strip()]
    regions: list[str] = []
    for state in states:
        if state in US_STATE_NAMES:
            regions.extend([state, US_STATE_NAMES[state]])
    return regions


def only_national_regions(regions: list[str]) -> bool:
    normalized_national = {normalize_region_value(region) for region in NATIONAL_REGION_ALIASES}
    normalized_regions = {normalize_region_value(region) for region in regions}
    return bool(normalized_regions) and normalized_regions <= normalized_national


def normalize_region_value(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def unique_regions(regions: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for region in regions:
        normalized = normalize_region_value(region)
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(region)
    return unique
