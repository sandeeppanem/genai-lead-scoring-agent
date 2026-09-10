import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.api import routes
from app.main import app
from app.services.score_storage import ScoreStorage


class APIContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.original_storage = routes.scoring_service.score_storage
        routes.scoring_service.score_storage = ScoreStorage(
            Path(cls.temp_dir.name) / "scores.json"
        )
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        routes.scoring_service.score_storage = cls.original_storage
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


if __name__ == "__main__":
    unittest.main()
