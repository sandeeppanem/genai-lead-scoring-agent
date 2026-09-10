from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from ..ml.features import DISPLAY_COLUMNS, normalize_sales_data


class DataService:
    """Read-only adapter for the B2B sales opportunity sample."""

    DEFAULT_DATA_PATH = (
        Path(__file__).resolve().parents[2]
        / "data"
        / "b2b"
        / "sales_win_loss.csv"
    )

    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = Path(data_path or self.DEFAULT_DATA_PATH)
        if not self.data_path.exists():
            raise FileNotFoundError(f"B2B dataset not found: {self.data_path}")
        self.dataframe = normalize_sales_data(pd.read_csv(self.data_path))

    @property
    def record_count(self) -> int:
        return int(len(self.dataframe))

    def get_opportunities(
        self, page: int = 1, page_size: int = 20, search: Optional[str] = None
    ) -> Dict[str, Any]:
        frame = self.dataframe
        if search:
            query = str(search).strip().lower()
            searchable = [
                "opportunity_number",
                "supplies_subgroup",
                "supplies_group",
                "region",
                "route_to_market",
                "competitor_type",
            ]
            mask = pd.Series(False, index=frame.index)
            for column in searchable:
                mask |= frame[column].astype(str).str.lower().str.contains(
                    query, regex=False, na=False
                )
            frame = frame[mask]

        total = int(len(frame))
        start = (page - 1) * page_size
        page_frame = frame.iloc[start : start + page_size]
        return {
            "opportunities": self._records(page_frame),
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_opportunity(self, record_id: int) -> Optional[Dict[str, Any]]:
        matches = self.dataframe[self.dataframe["record_id"].eq(record_id)]
        if matches.empty:
            return None
        return self._records(matches.iloc[:1])[0]

    def get_opportunities_by_ids(self, record_ids: List[int]) -> List[Dict[str, Any]]:
        requested_order = {record_id: index for index, record_id in enumerate(record_ids)}
        matches = self.dataframe[self.dataframe["record_id"].isin(record_ids)].copy()
        matches["_requested_order"] = matches["record_id"].map(requested_order)
        matches = matches.sort_values("_requested_order")
        return self._records(matches)

    def get_statistics(self) -> Dict[str, Any]:
        frame = self.dataframe
        won = int(frame["target"].sum())
        total = int(len(frame))
        return {
            "dataset": "IBM Watson Sales Win/Loss sample",
            "total_opportunities": total,
            "won_opportunities": won,
            "lost_opportunities": total - won,
            "win_rate": round(won / total * 100, 2),
            "average_opportunity_amount_usd": round(
                float(frame["opportunity_amount_usd"].mean()), 2
            ),
            "total_pipeline_amount_usd": round(
                float(frame["opportunity_amount_usd"].sum()), 2
            ),
            "supplies_groups": self._dimension_summary("supplies_group"),
            "regions": self._dimension_summary("region"),
            "routes_to_market": self._dimension_summary("route_to_market"),
            "competitor_types": self._dimension_summary("competitor_type"),
            "data_limitations": [
                "No event dates are present, so evaluation cannot be time-based.",
                "No notes, emails, contact PII, or account identifiers are present.",
                "Outcome is displayed only for demo comparison and never enters scoring.",
            ],
        }

    def dimension_values(self, column: str) -> List[str]:
        if column not in self.dataframe:
            return []
        return sorted(self.dataframe[column].dropna().astype(str).unique().tolist())

    def filtered_frame(self, filters: Dict[str, str]) -> pd.DataFrame:
        frame = self.dataframe
        for column, value in filters.items():
            if column in frame:
                frame = frame[frame[column].astype(str).str.casefold().eq(value.casefold())]
        return frame

    def _dimension_summary(self, column: str) -> Dict[str, Dict[str, float]]:
        grouped = self.dataframe.groupby(column, dropna=False).agg(
            opportunities=("record_id", "count"),
            wins=("target", "sum"),
            average_amount_usd=("opportunity_amount_usd", "mean"),
        )
        output: Dict[str, Dict[str, float]] = {}
        for key, row in grouped.iterrows():
            count = int(row["opportunities"])
            output[str(key)] = {
                "opportunities": count,
                "wins": int(row["wins"]),
                "win_rate": round(float(row["wins"]) / count * 100, 2),
                "average_amount_usd": round(float(row["average_amount_usd"]), 2),
            }
        return output

    @staticmethod
    def _records(frame: pd.DataFrame) -> List[Dict[str, Any]]:
        clean = frame[DISPLAY_COLUMNS].where(pd.notna(frame[DISPLAY_COLUMNS]), None)
        return clean.to_dict(orient="records")
