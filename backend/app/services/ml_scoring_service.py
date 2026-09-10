from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
from xgboost import DMatrix

from ..ml.features import CATEGORICAL_FEATURES, FEATURE_COLUMNS, features_from_records
from .policy_service import PolicyService
from .score_storage import ScoreStorage


FACTOR_LABELS = {
    "log_opportunity_amount_usd": "Opportunity amount",
    "client_size_by_revenue": "Client revenue band",
    "client_size_by_employee_count": "Client employee band",
    "revenue_from_client_past_two_years": "Prior client revenue band",
    "supplies_subgroup": "Product subgroup",
    "supplies_group": "Product group",
    "region": "Region",
    "route_to_market": "Route to market",
    "competitor_type": "Competitor status",
}


class MLScoringService:
    DEFAULT_ARTIFACT_PATH = (
        Path(__file__).resolve().parents[2]
        / "models"
        / "b2b_opportunity_model.joblib"
    )
    DEFAULT_METADATA_PATH = (
        Path(__file__).resolve().parents[2]
        / "models"
        / "b2b_opportunity_model.json"
    )

    def __init__(
        self,
        artifact_path: Optional[Path] = None,
        metadata_path: Optional[Path] = None,
        score_storage: Optional[ScoreStorage] = None,
    ):
        self.artifact_path = Path(artifact_path or self.DEFAULT_ARTIFACT_PATH)
        self.metadata_path = Path(metadata_path or self.DEFAULT_METADATA_PATH)
        self.score_storage = score_storage or ScoreStorage()
        self.artifact: Optional[Dict[str, Any]] = None
        self.load_error: Optional[str] = None
        self._load_artifact()

    @property
    def is_ready(self) -> bool:
        return self.artifact is not None

    @property
    def model_version(self) -> Optional[str]:
        return self.artifact.get("model_version") if self.artifact else None

    def _load_artifact(self) -> None:
        if not self.artifact_path.exists():
            self.load_error = (
                f"Model artifact not found at {self.artifact_path}. "
                "Run: python backend/scripts/train_model.py"
            )
            return
        try:
            self.artifact = joblib.load(self.artifact_path)
            self.load_error = None
        except Exception as error:
            self.load_error = f"Unable to load model artifact: {error}"
            self.artifact = None

    def get_model_card(self) -> Dict[str, Any]:
        if not self.metadata_path.exists():
            return {
                "ready": self.is_ready,
                "model_version": self.model_version,
                "error": self.load_error,
            }
        metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        metadata["ready"] = self.is_ready
        if self.load_error:
            metadata["error"] = self.load_error
        return metadata

    def score_opportunities(
        self, opportunities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if not self.artifact:
            raise RuntimeError(self.load_error or "ML model is not ready")
        if not opportunities:
            return []

        results: Dict[int, Dict[str, Any]] = {}
        pending: List[Dict[str, Any]] = []
        for opportunity in opportunities:
            input_hash = self._input_hash(opportunity)
            cached = self.score_storage.get_score(opportunity["record_id"])
            if (
                cached
                and cached.get("model_version") == self.model_version
                and cached.get("input_hash") == input_hash
            ):
                results[opportunity["record_id"]] = cached
            else:
                pending.append(opportunity)

        if pending:
            feature_frame = features_from_records(pending)
            transformed = self.artifact["preprocessor"].transform(feature_frame)
            model = self.artifact["model"]
            raw_margin = model.predict(transformed, output_margin=True)
            probability = self.artifact["calibrator"].predict_proba(
                raw_margin.reshape(-1, 1)
            )[:, 1]
            shap_rows = model.get_booster().predict(
                DMatrix(transformed), pred_contribs=True
            )

            new_scores = []
            for index, opportunity in enumerate(pending):
                score = self._build_score(
                    opportunity, float(probability[index]), shap_rows[index]
                )
                new_scores.append(score)
                results[opportunity["record_id"]] = score
            self.score_storage.store_scores(new_scores)

        return [results[item["record_id"]] for item in opportunities]

    def _build_score(
        self, opportunity: Dict[str, Any], probability: float, shap_row: np.ndarray
    ) -> Dict[str, Any]:
        factors = self._top_factors(opportunity, shap_row[:-1])
        positives = [factor for factor in factors if factor["direction"] == "increases"]
        negatives = [factor for factor in factors if factor["direction"] == "decreases"]
        explanation_parts = [
            f"Calibrated win probability is {probability * 100:.1f}%.",
        ]
        if positives:
            explanation_parts.append(
                "Strongest positive signal: "
                f"{positives[0]['label']} = {positives[0]['value']}."
            )
        if negatives:
            explanation_parts.append(
                "Strongest negative signal: "
                f"{negatives[0]['label']} = {negatives[0]['value']}."
            )

        routing = PolicyService.route(
            probability,
            self.artifact["high_priority_threshold"],
            self.artifact["nurture_threshold"],
        )
        return {
            "record_id": int(opportunity["record_id"]),
            "opportunity_number": str(opportunity["opportunity_number"]),
            "score": int(round(probability * 100)),
            "probability": round(probability, 8),
            "explanation": " ".join(explanation_parts),
            "factors": factors,
            "explanation_method": self.artifact["explanation_method"],
            "routing": routing,
            "model_version": self.artifact["model_version"],
            "input_hash": self._input_hash(opportunity),
            "scored_at": datetime.now(timezone.utc).isoformat(),
        }

    def _top_factors(
        self, opportunity: Dict[str, Any], contributions: np.ndarray
    ) -> List[Dict[str, Any]]:
        grouped_contributions: Dict[str, float] = {}
        for transformed_name, contribution in zip(
            self.artifact["feature_names"], contributions
        ):
            feature = self._source_feature(transformed_name)
            grouped_contributions[feature] = grouped_contributions.get(
                feature, 0.0
            ) + float(contribution)

        candidates = []
        for feature, value in grouped_contributions.items():
            if abs(value) < 0.01:
                continue
            display_value = opportunity.get(
                "opportunity_amount_usd"
                if feature == "log_opportunity_amount_usd"
                else feature
            )
            candidates.append(
                {
                    "feature": feature,
                    "label": FACTOR_LABELS.get(feature, feature.replace("_", " ").title()),
                    "value": display_value,
                    "direction": "increases" if value > 0 else "decreases",
                    "shap_value": round(value, 6),
                }
            )

        positives = sorted(
            (item for item in candidates if item["shap_value"] > 0),
            key=lambda item: item["shap_value"],
            reverse=True,
        )[:3]
        negatives = sorted(
            (item for item in candidates if item["shap_value"] < 0),
            key=lambda item: item["shap_value"],
        )[:3]
        return positives + negatives

    @staticmethod
    def _source_feature(transformed_name: str) -> str:
        name = transformed_name.split("__", 1)[-1]
        if name in FEATURE_COLUMNS:
            return name
        for feature in CATEGORICAL_FEATURES:
            prefix = f"{feature}_"
            if name.startswith(prefix):
                return feature
        return name

    def _input_hash(self, opportunity: Dict[str, Any]) -> str:
        payload = {
            "model_version": self.model_version,
            "features": {
                key: opportunity.get(
                    "opportunity_amount_usd"
                    if key == "log_opportunity_amount_usd"
                    else key
                )
                for key in FEATURE_COLUMNS
            },
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
