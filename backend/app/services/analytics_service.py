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
        if any(word in text for word in ("highest", "largest", "biggest")) and any(
            word in text for word in ("amount", "value", "deal", "opportunit")
        ):
            return self.execute("highest_value", filters=filters)

        dimension, label = self._requested_dimension(text)
        if dimension:
            return self.execute(
                "observed_win_rate", dimension=dimension, filters=filters, label=label
            )

        return self.execute("portfolio_summary", filters=filters)

    def execute(
        self,
        operation: str,
        *,
        dimension: str = "",
        filters: Dict[str, str] = None,
        label: str = "",
    ) -> Dict[str, Any]:
        """Execute a structured allow-listed analytical operation."""
        filters = filters or {}
        supported_filters = {
            "region", "route_to_market", "supplies_group", "competitor_type"
        }
        if not set(filters).issubset(supported_filters):
            raise ValueError("Unsupported analytics filter")
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
                "operation": operation,
                "rows": [],
            }

        if operation == "highest_value":
            top = frame.nlargest(5, "opportunity_amount_usd")
            values = [
                f"#{row.record_id} (${row.opportunity_amount_usd:,.0f}, {row.region}, {row.route_to_market})"
                for row in top.itertuples()
            ]
            response = self._response(
                f"Highest-value opportunities: {', '.join(values)}.",
                frame,
                filters,
                time_window,
                top["record_id"].astype(int).tolist(),
            )
            response.update(
                {
                    "operation": operation,
                    "rows": [
                        {
                            "record_id": int(row.record_id),
                            "amount_usd": float(row.opportunity_amount_usd),
                            "region": str(row.region),
                            "route_to_market": str(row.route_to_market),
                        }
                        for row in top.itertuples()
                    ],
                }
            )
            return response

        if operation == "observed_win_rate":
            allowed_dimensions = {
                "region": "regions",
                "route_to_market": "routes to market",
                "supplies_group": "product groups",
                "competitor_type": "competitor statuses",
            }
            if dimension not in allowed_dimensions:
                raise ValueError("A supported grouping dimension is required")
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
                {
                    "value": str(row[dimension]),
                    "opportunities": int(row.opportunities),
                    "wins": int(row.wins),
                    "win_rate": round(float(row.win_rate) * 100, 2),
                    "average_amount_usd": round(float(row.average_amount), 2),
                }
                for _, row in summary.iterrows()
            ]
            text_rows = [
                f"{row['value']}: {row['win_rate']:.1f}% "
                f"({row['wins']}/{row['opportunities']})"
                for row in rows[:5]
            ]
            answer = (
                f"Top {label or allowed_dimensions[dimension]} by observed win rate: "
                f"{'; '.join(text_rows)}. Computed over {population_size:,} opportunities."
            )
            response = self._response(answer, frame, filters, time_window)
            response.update(
                {"operation": operation, "dimension": dimension, "rows": rows}
            )
            return response

        if operation != "portfolio_summary":
            raise ValueError("Unsupported analytics operation")

        wins = int(frame["target"].sum())
        answer = (
            f"The selected population contains {population_size:,} opportunities: "
            f"{wins:,} won and {population_size - wins:,} lost "
            f"({wins / population_size * 100:.1f}% observed win rate). "
            "Ask for win rate by region, route to market, product group, or competitor status."
        )
        response = self._response(answer, frame, filters, time_window)
        response.update(
            {
                "operation": operation,
                "rows": [
                    {
                        "opportunities": population_size,
                        "wins": wins,
                        "losses": population_size - wins,
                        "win_rate": round(wins / population_size * 100, 2),
                    }
                ],
            }
        )
        return response

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
