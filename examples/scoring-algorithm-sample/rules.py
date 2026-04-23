"""Deterministic scoring rules. Generated from data/target-description.md.
Hand-edit freely — this file is yours."""


def headcount_in_target_band(row: dict) -> bool:
    """Firmographic signature: headcount 50-300."""
    try:
        hc = int(row.get("headcount", 0))
    except (TypeError, ValueError):
        return False
    return 50 <= hc <= 300


def hq_in_northeast(row: dict) -> bool:
    """Firmographic signature: HQ in US Northeast."""
    return row.get("hq_state", "").upper() in {
        "NY", "MA", "CT", "NJ", "PA", "RI", "VT", "NH", "ME",
    }


def is_venture_backed(row: dict) -> bool:
    """Firmographic signature: private + institutional funding (Series A-C)."""
    ownership = row.get("ownership_type", "").lower()
    stage = row.get("funding_stage", "").lower()
    return ownership == "private" and any(
        s in stage for s in ("series a", "series b", "series c")
    )


def has_segment_in_stack(row: dict) -> bool:
    """Firmographic signature: Segment in tech stack (85% match rate in Closed-Won)."""
    stack = (row.get("tech_stack") or "").lower()
    return "segment" in stack


def has_modern_data_stack(row: dict) -> bool:
    """Interaction pattern: Snowflake AND dbt together in stack."""
    stack = (row.get("tech_stack") or "").lower()
    return "snowflake" in stack and "dbt" in stack


def in_target_industry(row: dict) -> bool:
    """Firmographic signature: MarTech / Analytics / Data Infra / Fintech."""
    industry = (row.get("industry") or "").lower()
    return any(
        kw in industry
        for kw in ("martech", "analytics", "data infra", "fintech", "commerce", "devtools")
    )


# Disqualifiers
def is_public(row: dict) -> bool:
    """Disqualifier: public companies — Closed-Won is 100% private."""
    return (row.get("ownership_type") or "").lower() == "public"


def is_non_us(row: dict) -> bool:
    """Disqualifier: non-US HQ."""
    country = (row.get("hq_country") or "").upper()
    return country not in ("", "US", "USA", "UNITED STATES")
