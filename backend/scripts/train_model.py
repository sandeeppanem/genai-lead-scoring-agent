#!/usr/bin/env python3
"""Train, calibrate, and evaluate the B2B opportunity scoring model."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Tuple

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.ml.features import (  # noqa: E402
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    LEAKAGE_COLUMNS,
    NUMERIC_FEATURES,
    normalize_sales_data,
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def grouped_split(
    frame: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Create 50/15/15/20 train/validation/calibration/test group splits."""

    groups = frame["opportunity_number"]
    outer = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=20260910)
    development_idx, test_idx = next(outer.split(frame, groups=groups))
    development = frame.iloc[development_idx]
    test = frame.iloc[test_idx]

    calibration_split = GroupShuffleSplit(
        n_splits=1, test_size=0.1875, random_state=20260911
    )
    train_validation_idx, calibration_relative_idx = next(
        calibration_split.split(
            development, groups=development["opportunity_number"]
        )
    )
    train_validation = development.iloc[train_validation_idx]
    calibration = development.iloc[calibration_relative_idx]

    validation_split = GroupShuffleSplit(
        n_splits=1, test_size=(15 / 65), random_state=20260912
    )
    train_relative_idx, validation_relative_idx = next(
        validation_split.split(
            train_validation, groups=train_validation["opportunity_number"]
        )
    )
    return (
        train_validation.iloc[train_relative_idx].copy(),
        train_validation.iloc[validation_relative_idx].copy(),
        calibration.copy(),
        test.copy(),
    )


def build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            (
                "numeric",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                NUMERIC_FEATURES,
            ),
            (
                "categorical",
                Pipeline(
                    steps=[
                        (
                            "imputer",
                            SimpleImputer(strategy="constant", fill_value="Unknown"),
                        ),
                        ("one_hot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                CATEGORICAL_FEATURES,
            ),
        ]
    )


def build_xgboost(max_depth: int) -> XGBClassifier:
    return XGBClassifier(
        n_estimators=300,
        max_depth=max_depth,
        learning_rate=0.04,
        min_child_weight=20,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_alpha=0.2,
        reg_lambda=8.0,
        objective="binary:logistic",
        eval_metric="logloss",
        n_jobs=4,
        random_state=42,
    )


def fit_platt_calibrator(raw_margin: np.ndarray, target: pd.Series) -> LogisticRegression:
    calibrator = LogisticRegression(C=1_000_000, solver="lbfgs", random_state=42)
    calibrator.fit(raw_margin.reshape(-1, 1), target)
    return calibrator


def calibrated_probabilities(
    model: XGBClassifier,
    calibrator: LogisticRegression,
    transformed_features,
) -> np.ndarray:
    raw_margin = model.predict(transformed_features, output_margin=True)
    return calibrator.predict_proba(raw_margin.reshape(-1, 1))[:, 1]


def evaluate(y_true: pd.Series, probabilities: np.ndarray) -> Dict[str, float]:
    top_count = max(1, int(np.ceil(len(y_true) * 0.10)))
    top_indices = np.argsort(-probabilities)[:top_count]
    prevalence = float(y_true.mean())
    precision_at_ten = float(y_true.iloc[top_indices].mean())
    return {
        "records": int(len(y_true)),
        "win_rate": round(prevalence, 6),
        "roc_auc": round(float(roc_auc_score(y_true, probabilities)), 6),
        "average_precision": round(
            float(average_precision_score(y_true, probabilities)), 6
        ),
        "brier_score": round(float(brier_score_loss(y_true, probabilities)), 6),
        "log_loss": round(float(log_loss(y_true, probabilities)), 6),
        "precision_at_top_10_percent": round(precision_at_ten, 6),
        "lift_at_top_10_percent": round(precision_at_ten / prevalence, 6),
    }


def train(data_path: Path, artifact_path: Path, metadata_path: Path) -> Dict:
    source_hash = file_sha256(data_path)
    data = normalize_sales_data(pd.read_csv(data_path))
    train_data, validation_data, calibration_data, test_data = grouped_split(data)

    # Hyperparameters are selected only on the validation groups.
    candidate_preprocessor = build_preprocessor()
    train_transformed = candidate_preprocessor.fit_transform(train_data[FEATURE_COLUMNS])
    validation_transformed = candidate_preprocessor.transform(
        validation_data[FEATURE_COLUMNS]
    )
    candidate_metrics = {}
    selected_depth = None
    selected_auc = -1.0
    for depth in (3, 4):
        candidate = build_xgboost(depth)
        candidate.fit(train_transformed, train_data["target"], verbose=False)
        candidate_probabilities = candidate.predict_proba(validation_transformed)[:, 1]
        candidate_metrics[f"max_depth_{depth}"] = evaluate(
            validation_data["target"], candidate_probabilities
        )
        candidate_auc = candidate_metrics[f"max_depth_{depth}"]["roc_auc"]
        if candidate_auc > selected_auc:
            selected_auc = candidate_auc
            selected_depth = depth

    # Refit on train + validation. Calibration and final test remain untouched.
    development_data = pd.concat([train_data, validation_data], ignore_index=True)
    preprocessor = build_preprocessor()
    development_transformed = preprocessor.fit_transform(
        development_data[FEATURE_COLUMNS]
    )
    calibration_transformed = preprocessor.transform(calibration_data[FEATURE_COLUMNS])
    test_transformed = preprocessor.transform(test_data[FEATURE_COLUMNS])

    model = build_xgboost(selected_depth)
    model.fit(development_transformed, development_data["target"], verbose=False)
    calibration_margin = model.predict(calibration_transformed, output_margin=True)
    calibrator = fit_platt_calibrator(calibration_margin, calibration_data["target"])

    probabilities = {
        "development": calibrated_probabilities(
            model, calibrator, development_transformed
        ),
        "calibration": calibrated_probabilities(
            model, calibrator, calibration_transformed
        ),
        "test": calibrated_probabilities(model, calibrator, test_transformed),
    }
    xgboost_metrics = {
        "development": evaluate(
            development_data["target"], probabilities["development"]
        ),
        "calibration": evaluate(
            calibration_data["target"], probabilities["calibration"]
        ),
        "test": evaluate(test_data["target"], probabilities["test"]),
    }

    # Honest benchmark only; logistic regression never produces online scores.
    logistic_pipeline = Pipeline(
        steps=[
            ("preprocessing", build_preprocessor()),
            (
                "classifier",
                LogisticRegression(max_iter=2_000, solver="liblinear", random_state=42),
            ),
        ]
    )
    logistic_pipeline.fit(development_data[FEATURE_COLUMNS], development_data["target"])
    logistic_calibrator = fit_platt_calibrator(
        logistic_pipeline.decision_function(calibration_data[FEATURE_COLUMNS]),
        calibration_data["target"],
    )
    logistic_test_probability = logistic_calibrator.predict_proba(
        logistic_pipeline.decision_function(test_data[FEATURE_COLUMNS]).reshape(-1, 1)
    )[:, 1]
    logistic_test_metrics = evaluate(test_data["target"], logistic_test_probability)

    feature_names = preprocessor.get_feature_names_out().tolist()
    high_priority_threshold = float(np.quantile(probabilities["calibration"], 0.80))
    nurture_threshold = float(np.quantile(probabilities["calibration"], 0.50))
    model_version = f"b2b-win-xgb-v1-{source_hash[:12]}"
    trained_at = datetime.now(timezone.utc).isoformat()

    artifact = {
        "preprocessor": preprocessor,
        "model": model,
        "calibrator": calibrator,
        "model_version": model_version,
        "feature_columns": FEATURE_COLUMNS,
        "feature_names": feature_names,
        "explanation_method": "xgboost_native_tree_shap",
        "high_priority_threshold": high_priority_threshold,
        "nurture_threshold": nurture_threshold,
        "source_sha256": source_hash,
        "trained_at": trained_at,
    }
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, artifact_path)

    metadata = {
        "model_version": model_version,
        "model_type": "xgboost_with_platt_calibration",
        "baseline_model": "logistic_regression_with_platt_calibration",
        "explanation_method": "XGBoost native TreeSHAP contributions on raw margin",
        "target": "opportunity_result_is_won",
        "prediction_point": "opportunity qualification snapshot",
        "dataset": {
            "name": "IBM Watson Sales Win/Loss sample",
            "rows_before_exact_deduplication": 78_025,
            "rows_used": int(len(data)),
            "source_sha256": source_hash,
        },
        "split": {
            "strategy": "grouped_random_50_15_15_20_by_opportunity_number",
            "warning": "The public sample has no event date; this is not a time-based test.",
            "train_rows": int(len(train_data)),
            "validation_rows": int(len(validation_data)),
            "calibration_rows": int(len(calibration_data)),
            "test_rows": int(len(test_data)),
        },
        "selection": {
            "selected_max_depth": selected_depth,
            "validation_candidates": candidate_metrics,
        },
        "features": FEATURE_COLUMNS,
        "excluded_leakage_columns": LEAKAGE_COLUMNS,
        "policy": {
            "high_priority_threshold": round(high_priority_threshold, 8),
            "nurture_threshold": round(nurture_threshold, 8),
            "high_priority_capacity": "top 20% of calibration opportunities",
        },
        "metrics": {
            "xgboost": xgboost_metrics,
            "logistic_regression_test_baseline": logistic_test_metrics,
        },
        "runtime": {
            "python": sys.version.split()[0],
            "scikit_learn": sklearn.__version__,
            "xgboost": xgboost.__version__,
        },
        "trained_at": trained_at,
        "limitations": [
            "The dataset contains no dates, notes, emails, or account identifiers.",
            "Evaluation is duplicate-safe but not temporal.",
            "This public sample validates architecture; production claims require timestamped company CRM snapshots.",
        ],
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data",
        type=Path,
        default=BACKEND_DIR / "data" / "b2b" / "sales_win_loss.csv",
    )
    parser.add_argument(
        "--artifact",
        type=Path,
        default=BACKEND_DIR / "models" / "b2b_opportunity_model.joblib",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=BACKEND_DIR / "models" / "b2b_opportunity_model.json",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    result = train(arguments.data, arguments.artifact, arguments.metadata)
    print(json.dumps(result, indent=2))
