import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.analytics_service import AnalyticsService
from app.services.command_service import CommandService
from app.services.data_service import DataService
from app.services.inquiry_service import InquiryService
from app.services.jev_service import JevService
from app.services.leadflow_service import LeadFlowService
from app.services.llm_service import LLMService
from app.services.ml_scoring_service import MLScoringService
from app.services.score_storage import ScoreStorage
from app.services.workflow_policy_service import WorkflowPolicyService


class LeadFlowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.data_service = DataService()
        cls.scoring_service = MLScoringService(
            score_storage=ScoreStorage(Path(cls.temp_dir.name) / "scores.json")
        )
        cls.inquiry_service = InquiryService(Path(cls.temp_dir.name) / "leadflow.db")
        with patch.dict("os.environ", {"TYPESAFE_MODE": "demo"}):
            cls.jev_service = JevService()
        cls.policy = WorkflowPolicyService()
        cls.leadflow = LeadFlowService(
            cls.data_service,
            cls.scoring_service,
            cls.inquiry_service,
            cls.jev_service,
            cls.policy,
        )
        cls.analytics = AnalyticsService(cls.data_service)
        cls.commands = CommandService(
            cls.data_service,
            cls.scoring_service,
            cls.analytics,
            LLMService(),
            cls.inquiry_service,
            cls.leadflow,
            cls.jev_service,
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    @staticmethod
    def _ml_score(route="nurture", score=25):
        return {"score": score, "routing": {"next_action": route}}

    def test_36_labeled_demo_inquiries_match_expected_intent_and_action(self):
        examples_path = (
            Path(__file__).resolve().parents[1]
            / "data"
            / "leadflow_synthetic_inquiries.json"
        )
        examples = json.loads(examples_path.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(examples), 30)
        products = self.data_service.dimension_values("supplies_group")
        for example in examples:
            with self.subTest(example=example["id"]):
                semantic = self.jev_service.classify_inquiry(example["text"], products)
                workflow = self.policy.decide(semantic, self._ml_score())
                self.assertEqual(
                    semantic["main_intent"]["value"], example["expected_intent"]
                )
                self.assertEqual(workflow["action"], example["expected_action"])
                self.assertEqual(semantic["provider_mode"], "demo")

    def test_support_and_opt_out_override_different_ml_scores(self):
        products = self.data_service.dimension_values("supplies_group")
        cases = [
            ("The tires arrived damaged and we need support.", "support"),
            ("Please stop contacting me.", "do_not_contact"),
        ]
        for text, expected_action in cases:
            semantic = self.jev_service.classify_inquiry(text, products)
            for route, score in (("low_priority", 5), ("sales_review", 90)):
                with self.subTest(text=text, route=route):
                    workflow = self.policy.decide(
                        semantic, self._ml_score(route=route, score=score)
                    )
                    self.assertEqual(workflow["action"], expected_action)
                    self.assertFalse(workflow["automated_outreach_allowed"])

    def test_high_ml_research_disagreement_is_visible(self):
        semantic = self.jev_service.classify_inquiry(
            "We are comparing tire suppliers for next year.",
            self.data_service.dimension_values("supplies_group"),
        )
        workflow = self.policy.decide(
            semantic, self._ml_score(route="sales_review", score=88)
        )
        self.assertEqual(workflow["action"], "nurture")
        self.assertIn("High ML propensity", workflow["disagreement"])

    def test_inquiry_is_dataset_bound_persisted_and_semantically_cached(self):
        text = "Please quote 200 replacement batteries; we need delivery next month."
        first = self.leadflow.create_inquiry(1, text)
        second = self.leadflow.create_inquiry(2, text)
        self.assertEqual(first["dataset_checksum"], self.data_service.dataset_checksum)
        self.assertEqual(first["workflow_decision"]["action"], "quote_request")
        self.assertFalse(first["semantic_decision"]["cache_hit"])
        self.assertTrue(second["semantic_decision"]["cache_hit"])
        queue = self.leadflow.list_queue(action="quote_request")
        self.assertEqual(queue["total"], 2)

    def test_commands_validate_filters_scope_and_selection(self):
        listed = self.commands.execute(
            "Show Pacific opportunities for Tires & Wheels.", [], []
        )
        self.assertEqual(listed["tool"], "list_opportunities")
        self.assertEqual(
            listed["interpreted_arguments"]["filters"],
            {"region": "Pacific", "supplies_group": "Tires & Wheels"},
        )
        self.assertGreater(listed["scope"]["matching_population"], 20)
        self.assertFalse(listed["scope"]["complete"])

        summary = self.commands.execute(
            "Compare observed win rates by sales channel.", [], []
        )
        self.assertEqual(summary["tool"], "summarize_portfolio")
        self.assertEqual(
            summary["interpreted_arguments"]["dimension"], "route_to_market"
        )
        self.assertEqual(summary["scope"]["ranking_scope"], "full matching population")

        scored = self.commands.execute("Score the selected opportunities.", [1, 2], [])
        self.assertEqual(scored["scope"]["scored"], 2)
        self.assertTrue(scored["scope"]["complete"])

    def test_commands_clarify_missing_ids_and_reject_date_filters(self):
        missing = self.commands.execute("Explain the selected opportunity.", [], [])
        self.assertIn("exactly one", missing["message"])
        dated = self.commands.execute(
            "Show Pacific opportunities since 2025.", [], []
        )
        self.assertEqual(dated["scope"]["time_window"], "unsupported")
        self.assertIn("no event timestamps", dated["message"])

    def test_status_command_previews_before_applying(self):
        inquiry = self.leadflow.create_inquiry(
            3, "The car electronics delivered to us are defective."
        )
        preview = self.commands.execute(
            "Mark the selected inquiry as reviewed.", [], [inquiry["id"]]
        )
        self.assertTrue(preview["requires_confirmation"])
        self.assertEqual(
            self.leadflow.get_inquiry(inquiry["id"])["status"], "new"
        )
        applied = self.commands.confirm(preview["confirmation_id"])
        self.assertEqual(applied["scope"]["updated"], 1)
        self.assertEqual(
            self.leadflow.get_inquiry(inquiry["id"])["status"], "reviewed"
        )


if __name__ == "__main__":
    unittest.main()
