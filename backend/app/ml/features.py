"""Canonical feature definitions shared by training and online scoring.

The source dataset contains several fields that summarize the complete sales
cycle.  Those fields are deliberately excluded because they would not be known
at the scoring point and would leak the outcome into the model.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable

import numpy as np
import pandas as pd


COLUMN_RENAMES = {
    "Opportunity Number": "opportunity_number",
    "Supplies Subgroup": "supplies_subgroup",
    "Supplies Group": "supplies_group",
    "Region": "region",
    "Route To Market": "route_to_market",
    "Elapsed Days In Sales Stage": "elapsed_days_in_sales_stage",
    "Opportunity Result": "outcome",
    "Sales Stage Change Count": "sales_stage_change_count",
    "Total Days Identified Through Closing": "total_days_identified_through_closing",
    "Total Days Identified Through Qualified": "total_days_identified_through_qualified",
    "Opportunity Amount USD": "opportunity_amount_usd",
    "Client Size By Revenue": "client_size_by_revenue",
    "Client Size By Employee Count": "client_size_by_employee_count",
    "Revenue From Client Past Two Years": "revenue_from_client_past_two_years",
    "Competitor Type": "competitor_type",
    "Ratio Days Identified To Total Days": "ratio_days_identified_to_total_days",
    "Ratio Days Validated To Total Days": "ratio_days_validated_to_total_days",
    "Ratio Days Qualified To Total Days": "ratio_days_qualified_to_total_days",
    "Deal Size Category": "deal_size_category",
}

CATEGORICAL_FEATURES = [
    "supplies_subgroup",
    "supplies_group",
    "region",
    "route_to_market",
    "competitor_type",
]

NUMERIC_FEATURES = [
    "log_opportunity_amount_usd",
    "client_size_by_revenue",
    "client_size_by_employee_count",
    "revenue_from_client_past_two_years",
]

FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES

LEAKAGE_COLUMNS = [
    "outcome",
    "elapsed_days_in_sales_stage",
    "sales_stage_change_count",
    "total_days_identified_through_closing",
    "total_days_identified_through_qualified",
    "ratio_days_identified_to_total_days",
    "ratio_days_validated_to_total_days",
    "ratio_days_qualified_to_total_days",
    "deal_size_category",
]

DISPLAY_COLUMNS = [
    "record_id",
    "opportunity_number",
    "supplies_subgroup",
    "supplies_group",
    "region",
    "route_to_market",
    "opportunity_amount_usd",
    "client_size_by_revenue",
    "client_size_by_employee_count",
    "revenue_from_client_past_two_years",
    "competitor_type",
    "deal_size_category",
    "outcome",
]


def normalize_sales_data(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a typed, snake-case copy of the IBM sales sample."""

    normalized = frame.rename(columns=COLUMN_RENAMES).copy()
    missing = set(COLUMN_RENAMES.values()) - set(normalized.columns)
    if missing:
        raise ValueError(f"Sales dataset is missing required columns: {sorted(missing)}")

    normalized = normalized.drop_duplicates().reset_index(drop=True)
    normalized.insert(0, "record_id", np.arange(1, len(normalized) + 1))
    normalized["opportunity_number"] = normalized["opportunity_number"].astype(str)
    normalized["competitor_type"] = normalized["competitor_type"].fillna("Unknown")

    numeric_columns = [
        "opportunity_amount_usd",
        "client_size_by_revenue",
        "client_size_by_employee_count",
        "revenue_from_client_past_two_years",
        "deal_size_category",
    ]
    for column in numeric_columns:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    amount = normalized["opportunity_amount_usd"].clip(lower=0).fillna(0)
    normalized["log_opportunity_amount_usd"] = np.log1p(amount)
    normalized["target"] = normalized["outcome"].eq("Won").astype(int)
    return normalized


def features_from_records(records: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Build the exact online feature frame expected by the trained model."""

    frame = pd.DataFrame(list(records))
    if frame.empty:
        return pd.DataFrame(columns=FEATURE_COLUMNS)

    if "log_opportunity_amount_usd" not in frame:
        raw_amount = frame.get(
            "opportunity_amount_usd", pd.Series(np.nan, index=frame.index)
        )
        amount = pd.to_numeric(raw_amount, errors="coerce")
        frame["log_opportunity_amount_usd"] = np.log1p(amount.clip(lower=0).fillna(0))

    for column in FEATURE_COLUMNS:
        if column not in frame:
            frame[column] = np.nan
    return frame[FEATURE_COLUMNS]
