from __future__ import annotations

from typing import Any, Dict, Tuple

import pandas as pd

from .data_service import DataService


class AnalyticsService:
    """Allow-listed analytical operations over the complete eligible dataset."""

    DIMENSIONS = {
        "region": ("region", "regions"),
        "route": ("route_to_market", "routes to market"),
        "channel": ("route_to_market", "routes to market"),
        "product": ("supplies_group", "product groups"),
        "supplies": ("supplies_group", "product groups"),
        "competitor": ("competitor_type", "competitor statuses"),
    }

    def __init__(self, data_service: DataService):
        self.data_service = data_service

    def answer(self, question: str) -> Dict[str, Any]:
        text = question.casefold()
        filters = self._extract_filters(text)
        frame = self.data_service.filtered_frame(filters)
        population_size = int(len(frame))
        time_window = "Single source reporting period; the dataset provides no dates."

        if population_size == 0:
            return {
                "answer": "No opportunities match the requested filters.",
                "population_size": 0,
                "filters": filters,
                "time_window": time_window,
                "sources": [],
            }

        if any(word in text for word in ("highest", "largest", "biggest")) and any(
            word in text for word in ("amount", "value", "deal", "opportunit")
        ):
            top = frame.nlargest(5, "opportunity_amount_usd")
            values = [
                f"#{row.record_id} (${row.opportunity_amount_usd:,.0f}, {row.region}, {row.route_to_market})"
                for row in top.itertuples()
            ]
            return self._response(
                f"Highest-value opportunities: {', '.join(values)}.",
                frame,
                filters,
                time_window,
                top["record_id"].astype(int).tolist(),
            )

        dimension, label = self._requested_dimension(text)
        if dimension:
            summary = (
                frame.groupby(dimension, dropna=False)
                .agg(
                    opportunities=("record_id", "count"),
                    wins=("target", "sum"),
                    average_amount=("opportunity_amount_usd", "mean"),
                )
                .reset_index()
            )
            summary["win_rate"] = summary["wins"] / summary["opportunities"]
            summary = summary.sort_values(
                ["win_rate", "opportunities"], ascending=[False, False]
            )
            rows = [
                f"{row[dimension]}: {row.win_rate * 100:.1f}% "
                f"({int(row.wins)}/{int(row.opportunities)})"
                for _, row in summary.head(5).iterrows()
            ]
            answer = (
                f"Top {label} by observed win rate: {'; '.join(rows)}. "
                f"Computed over {population_size:,} opportunities."
            )
            return self._response(answer, frame, filters, time_window)

        wins = int(frame["target"].sum())
        answer = (
            f"The selected population contains {population_size:,} opportunities: "
            f"{wins:,} won and {population_size - wins:,} lost "
            f"({wins / population_size * 100:.1f}% observed win rate). "
            "Ask for win rate by region, route to market, product group, or competitor status."
        )
        return self._response(answer, frame, filters, time_window)

    def _requested_dimension(self, text: str) -> Tuple[str, str]:
        for keyword, definition in self.DIMENSIONS.items():
            if keyword in text:
                return definition
        return "", ""

    def _extract_filters(self, text: str) -> Dict[str, str]:
        filters: Dict[str, str] = {}
        for column in (
            "region",
            "route_to_market",
            "supplies_group",
            "competitor_type",
        ):
            for value in self.data_service.dimension_values(column):
                if value.casefold() in text:
                    filters[column] = value
                    break
        return filters

    @staticmethod
    def _response(
        answer: str,
        frame: pd.DataFrame,
        filters: Dict[str, str],
        time_window: str,
        sources=None,
    ) -> Dict[str, Any]:
        return {
            "answer": answer,
            "population_size": int(len(frame)),
            "filters": filters,
            "time_window": time_window,
            "sources": sources or [],
        }
