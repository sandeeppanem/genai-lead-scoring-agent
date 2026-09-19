import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from app.ml.features import FEATURE_COLUMNS, LEAKAGE_COLUMNS, normalize_sales_data
from app.services.analytics_service import AnalyticsService
from app.services.data_service import DataService
from app.services.llm_service import LLMService
from app.services.ml_scoring_service import MLScoringService
from app.services.score_storage import ScoreStorage


class HybridPipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_service = DataService()
        cls.temporary_directory = tempfile.TemporaryDirectory()
        cls.scoring_service = MLScoringService(
            score_storage=ScoreStorage(
                Path(cls.temporary_directory.name) / "scores.json"
            )
        )

    @classmethod
    def tearDownClass(cls):
        cls.temporary_directory.cleanup()

    def test_dataset_is_b2b_and_exact_duplicates_are_removed(self):
        self.assertEqual(self.data_service.record_count, 77_970)
        first = self.data_service.get_opportunity(1)
        self.assertEqual(first["opportunity_number"], "1641984")
        self.assertIn(first["outcome"], {"Won", "Loss"})
        self.assertNotIn("company", first)
        self.assertNotIn("email", first)

    def test_product_taxonomy_is_derived_from_dataset_groups_and_subgroups(self):
        taxonomy = self.data_service.product_taxonomy()
        self.assertEqual(
            taxonomy["Car Accessories"],
            [
                "Batteries & Accessories",
                "Exterior Accessories",
                "Garage & Car Care",
                "Interior Accessories",
                "Replacement Parts",
                "Towing & Hitches",
            ],
        )
        self.assertEqual(len(taxonomy), 4)
        self.assertEqual(sum(map(len, taxonomy.values())), 11)

    def test_feature_contract_excludes_outcome_and_sales_cycle_leakage(self):
        self.assertTrue(set(FEATURE_COLUMNS).isdisjoint(LEAKAGE_COLUMNS))
        self.assertNotIn("outcome", FEATURE_COLUMNS)
        self.assertNotIn("deal_size_category", FEATURE_COLUMNS)

    def test_score_is_calibrated_model_output_with_tree_shap_factors(self):
        opportunities = self.data_service.get_opportunities_by_ids([1, 2, 3])
        scores = self.scoring_service.score_opportunities(opportunities)
        self.assertEqual([score["record_id"] for score in scores], [1, 2, 3])
        for score in scores:
            self.assertGreaterEqual(score["probability"], 0)
            self.assertLessEqual(score["probability"], 1)
            self.assertEqual(score["score"], round(score["probability"] * 100))
            self.assertEqual(
                score["explanation_method"], "xgboost_native_tree_shap"
            )
            self.assertTrue(score["factors"])
            self.assertEqual(
                len({factor["feature"] for factor in score["factors"]}),
                len(score["factors"]),
            )
            self.assertFalse(score["routing"]["automated_outreach_allowed"])

    def test_score_cache_is_versioned_and_input_hashed(self):
        opportunity = self.data_service.get_opportunities_by_ids([3])
        first = self.scoring_service.score_opportunities(opportunity)[0]
        second = self.scoring_service.score_opportunities(opportunity)[0]
        self.assertEqual(first, second)
        self.assertEqual(first["model_version"], self.scoring_service.model_version)
        self.assertEqual(len(first["input_hash"]), 64)

    def test_analytics_reports_population_and_scope(self):
        result = AnalyticsService(self.data_service).answer(
            "Which routes to market have the best win rate?"
        )
        self.assertEqual(result["population_size"], 77_970)
        self.assertEqual(result["filters"], {})
        self.assertIn("Reseller: 27.6% (9578/34738)", result["answer"])
        self.assertIn("Computed over 77,970 opportunities", result["answer"])
        self.assertIn("no dates", result["time_window"])

    def test_analytics_applies_multiple_verified_filters(self):
        result = AnalyticsService(self.data_service).answer(
            "What is the win rate for Telecoverage in Midwest?"
        )
        self.assertEqual(
            result["filters"],
            {"region": "Midwest", "route_to_market": "Telecoverage"},
        )
        self.assertEqual(result["population_size"], 102)
        self.assertIn("12 won and 90 lost", result["answer"])

    def test_analytics_returns_source_ids_for_ranked_records(self):
        result = AnalyticsService(self.data_service).answer(
            "What are the highest-value opportunities in Midwest?"
        )
        self.assertEqual(result["filters"], {"region": "Midwest"})
        self.assertEqual(result["population_size"], 21_013)
        self.assertEqual(result["sources"], [155, 162, 413, 2868, 4571])

    def test_normalizer_rejects_incomplete_schema(self):
        with self.assertRaises(ValueError):
            normalize_sales_data(pd.DataFrame({"Opportunity Result": ["Won"]}))

    def test_llm_is_disabled_by_default_even_when_a_key_exists(self):
        with patch.dict(
            "os.environ",
            {
                "ANTHROPIC_API_KEY": "server-side-test-value",
                "ENABLE_LLM_EXPLANATIONS": "false",
            },
        ):
            service = LLMService()

        self.assertFalse(service.enabled)
        self.assertFalse(service.is_ready)


if __name__ == "__main__":
    unittest.main()
