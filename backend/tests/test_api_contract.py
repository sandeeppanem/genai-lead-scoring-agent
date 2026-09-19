import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.api import routes
from app.main import app
from app.services.score_storage import ScoreStorage
from app.services.command_service import CommandService
from app.services.inquiry_service import InquiryService
from app.services.jev_service import JevService
from app.services.leadflow_service import LeadFlowService
from app.services.workflow_policy_service import WorkflowPolicyService


class APIContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.original_storage = routes.scoring_service.score_storage
        cls.original_inquiry_service = routes.inquiry_service
        cls.original_jev_service = routes.jev_service
        cls.original_leadflow_service = routes.leadflow_service
        cls.original_command_service = routes.command_service
        routes.scoring_service.score_storage = ScoreStorage(
            Path(cls.temp_dir.name) / "scores.json"
        )
        routes.inquiry_service = InquiryService(
            Path(cls.temp_dir.name) / "leadflow.db"
        )
        routes.jev_service = JevService()
        routes.leadflow_service = LeadFlowService(
            routes.data_service,
            routes.scoring_service,
            routes.inquiry_service,
            routes.jev_service,
            WorkflowPolicyService(),
        )
        routes.command_service = CommandService(
            routes.data_service,
            routes.scoring_service,
            routes.analytics_service,
            routes.llm_service,
            routes.inquiry_service,
            routes.leadflow_service,
            routes.jev_service,
        )
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        routes.scoring_service.score_storage = cls.original_storage
        routes.inquiry_service = cls.original_inquiry_service
        routes.jev_service = cls.original_jev_service
        routes.leadflow_service = cls.original_leadflow_service
        routes.command_service = cls.original_command_service
        cls.client.close()
        cls.temp_dir.cleanup()

    def test_end_to_end_api_contract(self):
        health = self.client.get("/api/health")
        model = self.client.get("/api/model")
        stats = self.client.get("/api/stats")
        opportunities = self.client.get("/api/opportunities?page_size=3")
        scores = self.client.post(
            "/api/opportunities/score", json={"record_ids": [1, 2]}
        )
        explanation = self.client.post("/api/opportunities/1/explanation")
        analytics = self.client.post(
            "/api/question",
            json={"question": "Which regions have the highest win rate?"},
        )

        for response in (
            health,
            model,
            stats,
            opportunities,
            scores,
            explanation,
            analytics,
        ):
            self.assertEqual(response.status_code, 200, response.text)

        self.assertEqual(
            health.json()["services"]["ml_model"]["status"], "operational"
        )
        self.assertEqual(model.json()["metrics"]["xgboost"]["test"]["roc_auc"], 0.821477)
        self.assertEqual(opportunities.json()["page_size"], 3)
        self.assertEqual(len(scores.json()), 2)
        self.assertTrue(all(score["factors"] for score in scores.json()))
        self.assertEqual(explanation.json()["score"], scores.json()[0]["score"])
        self.assertEqual(
            explanation.json()["routing"], scores.json()[0]["routing"]
        )
        self.assertEqual(explanation.json()["generated_by"], "deterministic_fallback")
        self.assertEqual(analytics.json()["population_size"], 77_970)

    def test_vercel_production_origin_is_allowed(self):
        origin = "https://genai-lead-scoring-agent.vercel.app"
        response = self.client.options(
            "/api/stats",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["access-control-allow-origin"], origin)

    def test_local_development_origins_are_allowed(self):
        for origin in (
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3002",
            "http://127.0.0.1:4173",
        ):
            with self.subTest(origin=origin):
                response = self.client.options(
                    "/api/stats",
                    headers={
                        "Origin": origin,
                        "Access-Control-Request-Method": "GET",
                    },
                )

                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(
                    response.headers["access-control-allow-origin"], origin
                )

    def test_public_api_has_no_cache_delete_operation(self):
        response = self.client.delete("/api/scores")
        self.assertEqual(response.status_code, 405, response.text)

    def test_public_scoring_batch_is_limited_to_one_page(self):
        response = self.client.post(
            "/api/opportunities/score",
            json={"record_ids": list(range(1, 22))},
        )
        self.assertEqual(response.status_code, 422, response.text)

    def test_leadflow_and_command_api_contract(self):
        created = self.client.post(
            "/api/inquiries",
            json={
                "record_id": 1,
                "inquiry_text": "Please quote 200 replacement batteries; we need delivery next month.",
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        item = created.json()
        self.assertEqual(item["workflow_decision"]["action"], "quote_request")
        self.assertEqual(item["semantic_decision"]["provider_mode"], "demo")
        self.assertNotEqual(
            item["semantic_decision"]["main_intent"]["probabilities"],
            item["ml_score"]["probability"],
        )

        queue = self.client.get("/api/action-queue?action=quote_request")
        self.assertEqual(queue.status_code, 200, queue.text)
        self.assertEqual(queue.json()["total"], 1)

        command = self.client.post(
            "/api/commands",
            json={"command": "Explain the score for record 1."},
        )
        self.assertEqual(command.status_code, 200, command.text)
        self.assertEqual(command.json()["tool"], "explain_opportunity")
        self.assertEqual(command.json()["result"]["record_id"], 1)

        preview = self.client.post(
            "/api/commands",
            json={
                "command": "Mark the selected inquiry as reviewed.",
                "selected_inquiry_ids": [item["id"]],
            },
        )
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertTrue(preview.json()["requires_confirmation"])
        confirmation = self.client.post(
            "/api/commands/confirm",
            json={"confirmation_id": preview.json()["confirmation_id"]},
        )
        self.assertEqual(confirmation.status_code, 200, confirmation.text)
        self.assertEqual(confirmation.json()["result"]["status"], "reviewed")


if __name__ == "__main__":
    unittest.main()
