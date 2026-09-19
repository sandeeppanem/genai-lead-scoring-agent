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
        taxonomy = self.data_service.product_taxonomy()
        for example in examples:
            with self.subTest(example=example["id"]):
                semantic = self.jev_service.classify_inquiry(example["text"], taxonomy)
                workflow = self.policy.decide(semantic, self._ml_score())
                self.assertEqual(
                    semantic["main_intent"]["value"], example["expected_intent"]
                )
                self.assertEqual(workflow["action"], example["expected_action"])
                self.assertEqual(semantic["provider_mode"], "demo")

    def test_support_and_opt_out_override_different_ml_scores(self):
        taxonomy = self.data_service.product_taxonomy()
        cases = [
            ("The tires arrived damaged and we need support.", "support"),
            ("Please stop contacting me.", "do_not_contact"),
        ]
        for text, expected_action in cases:
            semantic = self.jev_service.classify_inquiry(text, taxonomy)
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
            self.data_service.product_taxonomy(),
        )
        workflow = self.policy.decide(
            semantic, self._ml_score(route="sales_review", score=88)
        )
        self.assertEqual(workflow["action"], "nurture")
        self.assertEqual(workflow["base_priority"], "low")
        self.assertEqual(workflow["priority"], "medium")
        self.assertEqual(workflow["ml_priority_adjustment"], "raised")
        self.assertIn("High ML propensity", workflow["disagreement"])

    def test_ml_adjusts_only_safe_sales_workflow_priorities(self):
        taxonomy = self.data_service.product_taxonomy()
        product_fit = self.jev_service.classify_inquiry(
            "Are these replacement batteries suitable for our fleet?", taxonomy
        )
        high_fit = self.policy.decide(
            product_fit, self._ml_score(route="sales_review", score=88)
        )
        low_fit = self.policy.decide(
            product_fit, self._ml_score(route="low_priority", score=8)
        )
        self.assertEqual(high_fit["action"], "qualification")
        self.assertEqual(high_fit["base_priority"], "medium")
        self.assertEqual(high_fit["priority"], "high")
        self.assertEqual(high_fit["ml_priority_adjustment"], "raised")
        self.assertEqual(low_fit["action"], "qualification")
        self.assertEqual(low_fit["priority"], "medium")
        self.assertEqual(low_fit["ml_priority_adjustment"], "unchanged")

        research = self.jev_service.classify_inquiry(
            "We are researching battery suppliers.", taxonomy
        )
        low_research = self.policy.decide(
            research, self._ml_score(route="low_priority", score=8)
        )
        self.assertEqual(low_research["action"], "nurture")
        self.assertEqual(low_research["base_priority"], "medium")
        self.assertEqual(low_research["priority"], "low")
        self.assertEqual(low_research["ml_priority_adjustment"], "lowered")

    def test_urgency_and_operational_actions_are_never_downgraded_by_ml(self):
        taxonomy = self.data_service.product_taxonomy()
        urgent_qualification = self.jev_service.classify_inquiry(
            "We need pricing for batteries ASAP.", taxonomy
        )
        urgent_workflow = self.policy.decide(
            urgent_qualification, self._ml_score(route="low_priority", score=5)
        )
        self.assertEqual(urgent_workflow["action"], "qualification")
        self.assertEqual(urgent_workflow["priority"], "high")
        self.assertEqual(urgent_workflow["ml_priority_adjustment"], "unchanged")

        for text, expected_action in (
            ("The battery arrived broken and we need support.", "support"),
            ("Please stop contacting me.", "do_not_contact"),
        ):
            semantic = self.jev_service.classify_inquiry(text, taxonomy)
            workflow = self.policy.decide(
                semantic, self._ml_score(route="sales_review", score=95)
            )
            self.assertEqual(workflow["action"], expected_action)
            self.assertEqual(workflow["ml_priority_adjustment"], "not_applicable")

    def test_low_confidence_main_intent_routes_to_human_review(self):
        semantic = self.jev_service.classify_inquiry(
            "Thank you for sending the catalog.",
            self.data_service.product_taxonomy(),
        )
        workflow = self.policy.decide(
            semantic, self._ml_score(route="sales_review", score=95)
        )
        self.assertLess(
            semantic["main_intent"]["confidence"],
            self.policy.confidence_threshold,
        )
        self.assertEqual(workflow["action"], "human_review")
        self.assertEqual(workflow["priority"], "medium")
        self.assertEqual(workflow["ml_priority_adjustment"], "not_applicable")

    def test_gateway_question_uses_dataset_catalog_hierarchy(self):
        taxonomy = self.data_service.product_taxonomy()
        captured = {}

        def evaluate(state, questions):
            captured["state"] = state
            captured["questions"] = questions
            choices = {
                "main_intent": "quote_request",
                "product_interest": "car_accessories",
                "purchase_timeline": "within_30_days",
            }
            answers = {}
            for key, question in questions.items():
                if question["type"] == "choice":
                    selected = choices[key]
                    answers[key] = {
                        "type": "choice",
                        "choice": selected,
                        "probabilities": {
                            option: 1.0 if option == selected else 0.0
                            for option in question["criteria"]
                        },
                        "confidence": 1.0,
                    }
                else:
                    answers[key] = {"type": "noul", "noul": 0.9}
            return {"model": "typesafe-ai/jev", "answers": answers, "usage": {}}

        with patch.dict(
            "os.environ",
            {
                "TYPESAFE_MODE": "gateway",
                "JEV_GATEWAY_ADAPTER_URL": "https://example.test/api/jev",
                "JEV_ADAPTER_TOKEN": "test-token",
            },
        ):
            service = JevService()
        with patch.object(service, "_evaluate", side_effect=evaluate):
            decision = service.classify_inquiry(
                "Please quote 200 replacement batteries next month.", taxonomy
            )

        self.assertEqual(decision["product_interest"]["value"], "Car Accessories")
        self.assertEqual(decision["question_version"], "leadflow-inquiry-v2")
        self.assertEqual(captured["state"]["catalog_product_taxonomy"], taxonomy)
        self.assertIn(
            "Batteries & Accessories",
            captured["questions"]["product_interest"]["criteria"]["car_accessories"],
        )

    def test_gateway_command_reuses_catalog_hierarchy(self):
        taxonomy = self.data_service.product_taxonomy()
        dimensions = {
            "region": ["Pacific"],
            "route_to_market": ["Reseller"],
            "supplies_group": list(taxonomy),
            "competitor_type": ["Known"],
        }
        captured = {}

        def evaluate(state, questions):
            captured["state"] = state
            captured["questions"] = questions
            selections = {
                "tool": "list_opportunities",
                "summary_dimension": "not_specified",
                "queue_action": "not_specified",
                "workflow_status": "not_specified",
                "region": "pacific",
                "route_to_market": "not_specified",
                "supplies_group": "car_accessories",
                "competitor_type": "not_specified",
            }
            answers = {}
            for key, question in questions.items():
                selected = selections[key]
                answers[key] = {
                    "type": "choice",
                    "choice": selected,
                    "probabilities": {
                        option: 1.0 if option == selected else 0.0
                        for option in question["criteria"]
                    },
                    "confidence": 1.0,
                }
            return {"model": "typesafe-ai/jev", "answers": answers, "usage": {}}

        with patch.dict(
            "os.environ",
            {
                "TYPESAFE_MODE": "gateway",
                "JEV_GATEWAY_ADAPTER_URL": "https://example.test/api/jev",
                "JEV_ADAPTER_TOKEN": "test-token",
            },
        ):
            service = JevService()
        with patch.object(service, "_evaluate", side_effect=evaluate):
            decision = service.classify_command(
                "Show Pacific battery opportunities.", dimensions, taxonomy
            )

        self.assertEqual(decision["tool"], "list_opportunities")
        self.assertEqual(decision["arguments"]["region"], "Pacific")
        self.assertEqual(decision["arguments"]["supplies_group"], "Car Accessories")
        self.assertEqual(decision["question_version"], "leadflow-command-v2")
        self.assertEqual(captured["state"]["catalog_product_taxonomy"], taxonomy)
        self.assertIn(
            "Batteries & Accessories",
            captured["questions"]["supplies_group"]["criteria"]["car_accessories"],
        )

    def test_taxonomy_changes_invalidate_the_semantic_cache(self):
        text = "We are exploring towing hitches for a future fleet expansion."
        first = self.leadflow._classify(text)
        changed = self.data_service.product_taxonomy()
        changed["Car Accessories"] = [
            *changed["Car Accessories"],
            "New Catalog Subgroup",
        ]
        with patch.object(self.data_service, "product_taxonomy", return_value=changed):
            second = self.leadflow._classify(text)
        self.assertFalse(first["cache_hit"])
        self.assertFalse(second["cache_hit"])

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

        subgroup_listed = self.commands.execute(
            "Show Pacific opportunities for Batteries & Accessories.", [], []
        )
        self.assertEqual(subgroup_listed["tool"], "list_opportunities")
        self.assertEqual(
            subgroup_listed["interpreted_arguments"]["filters"],
            {"region": "Pacific", "supplies_group": "Car Accessories"},
        )

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
