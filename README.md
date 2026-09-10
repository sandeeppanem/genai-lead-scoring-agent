# Hybrid ML + GenAI B2B Opportunity Prioritization

A full-stack reference application that assigns calibrated B2B opportunity win
probabilities with XGBoost, explains the model with native TreeSHAP factors, and
keeps language generation outside the scoring path.

## What changed

The original prototype asked Claude to invent a 0–100 score for education leads
that were presented as B2B companies. The current design makes the ownership
boundary explicit:

- **XGBoost** learns win propensity from historical outcomes.
- **Platt calibration** turns raw model margins into probabilities.
- **Native TreeSHAP** identifies the factors that affected each prediction.
- **Policy code** assigns sales review, nurture, or low-priority actions.
- **Claude (optional)** verbalizes supplied evidence; it cannot alter the score.
- **Analytics tools** calculate answers over the complete matching population.

There is no RAG in this project. RAG would only be appropriate after adding an
approved knowledge base such as product material or sales policies.

## Dataset

The default dataset is the public IBM Watson Sales Win/Loss sample:

- 78,025 closed B2B opportunities; 77,970 after exact deduplication
- Product category, region, route to market, amount, client-size bands,
  prior-client-revenue band, competitor status, and Won/Loss outcome
- Public mirror and checksum documented in
  [backend/data/b2b/README.md](backend/data/b2b/README.md)

The IBM sample has no dates, account IDs, notes, or emails. Consequently, the
evaluation keeps repeated opportunity numbers in one split but cannot be
time-based. Treat the model as an architecture baseline, not a production
performance claim.

Only the active B2B source dataset is tracked. Generated score-cache data and
the retired education prototype dataset are intentionally excluded from the
repository.

## Model

Run training from the repository root:

~~~bash
python3 backend/scripts/train_model.py
~~~

Training uses four duplicate-safe groups:

- 50% training
- 15% XGBoost validation/model selection
- 15% probability calibration and capacity thresholds
- 20% untouched final testing

The current final test metrics are stored—not hardcoded—in
backend/models/b2b_opportunity_model.json.

| Metric | XGBoost | Logistic baseline |
| --- | ---: | ---: |
| ROC-AUC | 0.8215 | 0.7198 |
| Average precision | 0.6211 | 0.4407 |
| Brier score | 0.1303 | 0.1580 |
| Precision at top 10% | 74.0% | 59.4% |
| Top-decile lift | 3.19× | 2.56× |

Outcome, elapsed-stage days, stage changes, total-cycle duration, closing ratios,
and derived deal-size category are excluded from the feature pipeline.

## Run locally

Backend:

~~~bash
python3 -m venv backend/venv
source backend/venv/bin/activate
pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --reload --port 8000
~~~

Frontend:

~~~bash
cd frontend
npm install
npm start
~~~

The frontend uses /api by default. Set REACT_APP_API_URL for a separately hosted
backend. Optional Claude explanations require ANTHROPIC_API_KEY; ML scoring and
verified analytics do not.

## API

- GET /api/opportunities — paginated B2B opportunity records
- POST /api/opportunities/score — calibrated score, TreeSHAP factors, policy
- POST /api/opportunities/{record_id}/explanation — optional grounded narrative
- GET /api/model — model card, splits, leakage exclusions, metrics
- POST /api/question — allow-listed full-population analytics
- GET /api/stats — portfolio aggregates
- GET /api/health — real data/model/optional-LLM readiness

Example:

~~~bash
curl -X POST http://localhost:8000/api/opportunities/score \
  -H 'Content-Type: application/json' \
  -d '{"record_ids":[1,2,3]}'
~~~

## Verification

~~~bash
PYTHONPATH=backend python3 -m unittest discover -s backend/tests -v
cd frontend && npm run build
~~~

## Production path

See [docs/hybrid-architecture.md](docs/hybrid-architecture.md) for the target
point-in-time architecture, responsibility boundaries, rollout plan, and
acceptance gates. The next data milestone is timestamped CRM snapshots with a
fully matured outcome horizon; the next language milestone is validated intent
extraction with evidence spans from real historical notes.
