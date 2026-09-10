# Hybrid B2B opportunity prioritization

## Product definition

The application prioritizes a qualified B2B sales opportunity by estimating:

> P(opportunity is closed-won | fields available at the qualification snapshot)

The calibrated probability is the score. Language models cannot create or
modify it. This public sample does not include dates, so it cannot support a
defensible “won within N days” target; production data must add `scored_at`,
`qualified_at`, `closed_at`, and an explicit prediction horizon.

## Dataset decision

| Dataset | Domain | Size | Honest evaluation | Decision |
| --- | --- | ---: | --- | --- |
| X Education | Education enrollment | 9,240 | Leakage-screened random test ROC-AUC ~0.86 | Preserve, but retire from the B2B UI |
| Maven CRM opportunities | Simulated B2B hardware sales | 8,800 | Out-of-time ROC-AUC ~0.53 in our leakage-screened benchmark | Do not use as the primary model |
| IBM Watson Sales Win/Loss | B2B opportunity outcomes | 78,025 | Grouped XGBoost test ROC-AUC 0.8215; top-decile lift 3.19x | Use for the architecture baseline |

The IBM sample is superior for this repository's B2B purpose, but it is still a
sample dataset without dates, account IDs, or unstructured communications. It
must not be presented as proof of production performance.

## Target architecture

```text
CRM snapshot + consent state + engagement events
                         |
                         v
               point-in-time feature view <--- versioned LLM extraction
                         |                       + evidence spans
                         v
          calibrated ML propensity model
                         |
                  probability + rank
                         |
             verified model contributions
                         |
     deterministic policy (capacity, consent, SLA)
                         |
      grounded LLM explanation / outreach draft
                         |
        human-approved action + outcome event
                         |
             monitoring and delayed labels
```

Conversational analytics follows a separate path: the language model selects a
read-only, allow-listed aggregation; application code executes it over the full
eligible population; the model summarizes the returned table together with its
filters, row count, and time window. This is tool-grounding, not RAG. RAG is only
needed later if policy documents, product material, or playbooks become an
explanation source.

## Responsibility boundaries

| Layer | Owns | Must not do |
| --- | --- | --- |
| ML | Propensity, ranking, calibration | Read post-outcome fields or generated prose |
| LLM extraction | Typed intent from supplied text, with evidence | Invent missing facts or alter probability |
| Explanation | Render verified factors and evidence | Add unsupported reasons |
| Policy | Capacity, consent, routing, SLA | Delegate fixed thresholds to an LLM |
| Action | Draft/create a task after authorization | Send messages autonomously by default |

## Implementation sequence

1. **Baseline (implemented in this change):** B2B dataset adapter, four-way grouped
   split, logistic benchmark, calibrated XGBoost champion, native TreeSHAP factors,
   deterministic routing, metadata, and tests.
2. **Grounded UX:** B2B opportunity table, held-out metrics and calibration view,
   factor drawer, model version, and explicit data limitations.
3. **Language layer:** evidence-bearing extraction schema for actual notes/email;
   keep extracted fields out of ML until labeled text history proves lift.
4. **Analytics tools:** allow-listed group/filter/rank functions over all records;
   optional LLM planner with validated arguments and auditable results.
5. **Production data:** timestamped CRM snapshots, outcome maturation, rolling
   time splits, champion/challenger training, SHAP for the nonlinear challenger,
   drift/calibration monitoring, and outcome feedback.

## Production acceptance gates

- Zero post-outcome features in offline or online feature views.
- Time-based test set with a fully matured outcome horizon.
- Calibration error, Brier score, PR-AUC, and lift reported by segment.
- Policy thresholds selected from capacity and expected value, not accuracy.
- Model, feature, extraction, prompt, and policy versions stored per score.
- No score returned on operational failure; failures are explicit states.
- PII redaction, least-privilege access, consent enforcement, and an audit log.
