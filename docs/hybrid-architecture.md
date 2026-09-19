# System Architecture

## System objective

The application prioritizes qualified B2B sales opportunities by estimating a
calibrated closed-won probability from qualification-snapshot attributes. It
also classifies user-supplied inquiries into action queues and maps natural
language requests to a six-tool CRM registry. ML, semantic judgment, workflow
policy, and side effects remain separate contracts.

## Runtime architecture

```mermaid
flowchart TD
    subgraph Data
        CSV[(IBM Sales Win/Loss CSV)]
        DS[DataService]
        CSV --> DS
    end

    subgraph Scoring
        FC[Canonical feature contract]
        PP[Imputation, scaling, and one-hot encoding]
        XGB[XGBoost classifier]
        PC[Platt calibrator]
        TS[TreeSHAP source-feature aggregation]
        RP[Routing policy]

        FC --> PP --> XGB
        XGB --> PC
        XGB --> TS
        PC --> RP
    end

    subgraph Application
        UI[React application]
        API[FastAPI routes]
        LF[LeadFlow service]
        CMD[Command dispatcher]
        STORE[(Atomic JSON score cache)]
        INQUIRIES[(SQLite inquiries, history, cache, confirmations)]
        ANALYTICS[Structured analytics and approved tools]
        WF[Deterministic workflow policy]
        LLM[Optional explanation LLM]

        UI <--> API
        API --> LF
        API --> CMD
        API <--> STORE
        API <--> INQUIRIES
        API --> LLM --> API
        CMD --> ANALYTICS
        LF --> WF
    end

    subgraph Semantic evaluation
        JEV[Jev service]
        ADAPTER[Vercel server adapter]
        GATEWAY[Vercel AI Gateway: typesafe-ai/jev]

        JEV --> ADAPTER --> GATEWAY
    end

    DS --> FC
    DS --> ANALYTICS
    PC --> API
    TS --> API
    RP --> API
    DS --> LF
    LF --> JEV
    CMD --> JEV
    PC --> WF
    WF --> INQUIRIES
```

## Deployment topology and trust boundaries

```mermaid
flowchart LR
    USER[Anonymous browser]

    subgraph Vercel
        WEB[React production build]
        ADAPTER[Protected /api/jev function]
    end

    subgraph Render
        API[FastAPI service]
        MODEL[(Model and dataset artifacts)]
        STATE[(SQLite workflow state and JSON score cache)]
    end

    GW[Vercel AI Gateway]
    JEV[typesafe-ai/jev]

    USER -->|HTTPS application assets| WEB
    USER -->|HTTPS, CORS-restricted| API
    API -->|Shared adapter token| ADAPTER
    ADAPTER -->|Server-only Gateway key| GW
    GW --> JEV
    API --> MODEL
    API --> STATE
```

The browser receives neither provider credential nor the server-to-server
adapter token. Render validates public request shapes and rate limits anonymous
writes. The Vercel adapter authenticates Render, constrains evaluation payload
size and question count, applies a timeout, and normalizes Gateway results into
the backend's typed semantic contract.

## Scoring sequence

```mermaid
sequenceDiagram
    participant UI as React UI
    participant API as FastAPI
    participant Data as DataService
    participant ML as MLScoringService
    participant Cache as ScoreStorage
    participant Policy as PolicyService

    UI->>API: POST /api/opportunities/score {record_ids}
    API->>Data: Load requested opportunities
    Data-->>API: Qualification fields
    API->>ML: Score opportunities
    ML->>Cache: Check model version and input hash
    alt Valid cached result
        Cache-->>ML: Stored score
    else New or changed input
        ML->>ML: Transform features and predict margin
        ML->>ML: Calibrate probability and compute TreeSHAP
        ML->>Policy: Apply calibrated thresholds
        Policy-->>ML: Controlled routing decision
        ML->>Cache: Atomic score write
    end
    ML-->>API: Score, probability, factors, routing, versions
    API-->>UI: Typed OpportunityScore response
```

## Component contracts

| Component | Inputs | Outputs | Enforced behavior |
| --- | --- | --- | --- |
| `DataService` | Source CSV, pagination, search, filters | Typed opportunity records and aggregates | Read-only access and exact-match supported filters |
| Feature contract | Qualification-time record fields | Ordered model feature frame | Same schema in training and inference |
| XGBoost | Transformed feature matrix | Raw margin and propensity ranking | Outcome and completed-cycle fields are absent |
| Platt calibrator | Raw XGBoost margin | Calibrated probability | Fitted only on the calibration partition |
| TreeSHAP | XGBoost model and transformed row | Positive and negative source-feature factors | One-hot contributions aggregate to source business fields |
| `PolicyService` | Calibrated probability and thresholds | Priority and next action | Deterministic; automated outreach disabled |
| `LLMService` | Immutable score evidence | Explanation and missing-information narrative | Cannot write score, factors, model version, or routing |
| `AnalyticsService` | Natural-language question | Verified aggregate and scope metadata | Uses only allow-listed computations over matching records |
| `ScoreStorage` | Score result | Versioned cached result | Input-hash validation, locking, and atomic replacement |
| `JevService` | Inquiry or command plus dynamic choices | Typed semantic judgments | Demo, direct live, or protected Gateway mode; never executes a side effect |
| `InquiryService` | Inquiry, decisions, status, confirmation | Dataset-bound records and history | SQLite transactions; confirmation tokens are single-use |
| `LeadFlowService` | Linked record ID and inquiry text | Persisted decision trail | Semantic cache includes content, model, and question version |
| `WorkflowPolicyService` | Jev judgments and immutable ML score | Action, priority, reason, uncertainty | Deterministic; support/opt-out safety overrides; outreach disabled |
| `CommandService` | Jev tool choice, UI selection, explicit IDs | Validated tool result or clarification | Six-tool registry only; Python validates and executes |
| Vercel Jev adapter | Protected evaluation request | Normalized Choice/Noul answers and usage | Server-only key, request caps, timeout, retries, no state logging |

## Training architecture

The training script performs the following reproducible flow:

1. Verify and load the source dataset.
2. Normalize column names, types, outcomes, and exact duplicates.
3. Split opportunity-number groups into training, validation, calibration, and
   final-test partitions.
4. Fit the preprocessing pipeline on training data.
5. Select the configured XGBoost depth using validation ROC-AUC.
6. Refit preprocessing and XGBoost on training plus validation data.
7. Fit Platt calibration and capacity thresholds on the calibration partition.
8. Evaluate once on the untouched test partition.
9. Persist the model pipeline, calibrator, feature names, thresholds, source
   checksum, runtime versions, and model card.

## Analytics architecture

Conversational analytics is implemented as controlled application tooling. The
question parser selects a supported dimension or ranking operation, extracts
exact supported filters, and executes the calculation over all matching records.
The response reports:

- The computed answer
- Matching population size
- Applied filters
- Source record IDs for ranked opportunities
- The dataset time-window description

## LeadFlow architecture

LeadFlow stores user-supplied inquiry text separately from the historical
opportunity dataset. Each inquiry includes the linked record ID, opportunity
number, dataset version, and source checksum. The checksum is checked again on
read, preventing a future reorder or replacement of the CSV from silently
moving an inquiry to a different record.

Jev receives only the inquiry and the current product catalog. Independent
Choice and Noul judgments cover main intent, catalog product interest,
purchase timeline, urgency, concrete purchase requirement, and missing
qualification information. The workflow policy composes these judgments in
Python with the immutable ML score. It can therefore route an opt-out or
support issue correctly even when the opportunity's conversion score is high,
and it can show a high-score/early-research disagreement without confusing the
two probabilities.

`TYPESAFE_MODE=demo` uses deterministic rules and is explicitly marked in the
response. `TYPESAFE_MODE=live` calls TypeSafe's HTTP System One endpoint.
`TYPESAFE_MODE=gateway` calls the protected Vercel `/api/jev` function, which
uses AI SDK 7 `experimental_evaluate` with `typesafe-ai/jev`. The browser never
receives a provider credential. Gateway boolean answers are normalized to the
internal Noul shape, while categorical confidence is computed from the
returned probability distribution and labeled as application-derived.

### Inquiry sequence

```mermaid
sequenceDiagram
    participant User
    participant UI as React LeadFlow
    participant API as FastAPI
    participant Data as Data/ML services
    participant Jev as Jev service
    participant Policy as Workflow policy
    participant DB as SQLite

    User->>UI: Select one opportunity and create inquiry
    UI->>API: POST /api/inquiries
    API->>Data: Validate record, score, and load current dataset checksum
    API->>DB: Check semantic cache by content/model/question version
    alt Semantic cache miss
        API->>Jev: Shared state plus six focused questions
        Jev-->>API: Choice distributions and Noul probabilities
        API->>DB: Store semantic decision
    else Cache hit
        DB-->>API: Stored semantic decision
    end
    API->>Policy: Compose semantic judgment with immutable ML score
    Policy-->>API: Action, priority, reason, uncertainty, disagreement
    API->>DB: Store inquiry, decisions, dataset binding, and initial status
    API-->>UI: Complete inspectable decision trail
```

Jev is useful here because intent, urgency, missing information, and product
language are semantic rather than tabular. It is not permitted to estimate the
win probability or choose the final action. A low-confidence semantic answer
remains visible; policy can route it to qualification or human review.

## CRM command architecture

The command bar first obtains a constrained tool and categorical-argument
judgment, then Python parses explicit record/inquiry IDs and validates all
arguments against current dataset values. Only the six registered tools can
execute. Analytics commands call structured operations directly; they do not
feed an interpreted command back through the keyword parser. Listing reports
the matching population and returned page, aggregation reports its full
matching population, and date filters are rejected because the source has no
event timestamps. Status updates create a SQLite confirmation record before
any write and are applied only by the explicit confirmation endpoint.

### Command sequence

```mermaid
sequenceDiagram
    participant User
    participant UI as CRM command bar
    participant API as FastAPI
    participant Jev as Jev service
    participant Cmd as Command service
    participant Tool as Approved Python tool
    participant DB as SQLite

    User->>UI: Natural-language command plus current selection
    UI->>API: POST /api/commands
    API->>Jev: Command plus dynamic categorical choices
    Jev-->>Cmd: Tool choice, confidence, categorical arguments
    Cmd->>Cmd: Parse explicit IDs; validate choices, scope, and limits
    alt Read or scoring tool
        Cmd->>Tool: Execute allow-listed operation
        Tool-->>Cmd: Deterministic result
        Cmd-->>API: Result, interpreted arguments, and scope
        API-->>UI: Typed command response
    else Status update
        Cmd->>DB: Create pending single-use confirmation
        DB-->>Cmd: Confirmation ID
        Cmd-->>API: Preview only
        API-->>UI: Typed preview response
        User->>UI: Confirm change
        UI->>API: POST /api/commands/confirm
        API->>DB: Apply pending status and history atomically
        DB-->>UI: Confirmed result
    end
```

Jev is useful here for mapping varied wording to a constrained tool and known
categorical values. It does not parse record IDs, query data, score records,
calculate aggregates, or apply writes. Those operations remain deterministic
Python functions with typed responses.

## User-facing surfaces

| Surface | Capabilities | Decision source | External semantic cost |
| --- | --- | --- | --- |
| Model dashboard | Dataset profile, observed outcomes, held-out ROC-AUC, lift, feature contract, and model version | Dataset aggregates and persisted model card | None |
| Opportunities | Search, pagination, multi-select, batch scoring, calibrated probability, policy route, TreeSHAP factor inspection, and direct LeadFlow navigation | Data service, calibrated XGBoost, TreeSHAP, and deterministic scoring policy | None |
| LeadFlow inbox | Linked inquiry creation, six action queues, priority/status filters, full-text inspection, semantic uncertainty, ML/Jev disagreement, policy reason, and status management | Jev semantic evaluation plus deterministic workflow policy and persisted history | One Jev evaluation per new uncached inquiry |
| CRM command bar | Selection-aware use of six approved tools, interpreted arguments, result scope, clarification, and preview/confirmation for status writes | Jev tool/choice selection plus Python validation and execution | One Jev evaluation per command; confirmation itself is free |
| Verified analytics | Supported portfolio summaries, highest-value ranking, exact filters, and observed win-rate comparisons by business dimension | Deterministic full-population analytics | None |
| Grounded explanation API | Narrative score explanation and missing-information summary | Optional LLM wording wrapped around immutable ML and policy evidence | One explanation call when explicitly enabled |

## Decision ownership

| Decision or operation | Owner |
| --- | --- |
| Closed-won probability and 0–100 score | Calibrated XGBoost pipeline |
| Positive and negative model factors | TreeSHAP |
| Inquiry intent, product, timeline, urgency, requirement, missing information | Jev semantic evaluation |
| Command tool and supported categorical arguments | Jev semantic evaluation |
| Record/inquiry ID parsing and validation | Python command service |
| LeadFlow action, priority, explanation, disagreement, and outreach prohibition | Python workflow policy |
| Filters, scoring, explanations, rankings, and portfolio calculations | Approved Python tools |
| Status mutation | SQLite service after explicit confirmation |
| Optional narrative wording | Disabled-by-default explanation LLM |

## Security and reliability controls

- CORS origins are environment-configured and methods are restricted.
- API keys are loaded from environment variables and are never logged.
- Model readiness and load errors are exposed by the health endpoint.
- Scores are accepted from the calibrated ML service only.
- Cache hits require both the active model version and the exact input hash.
- The outcome is available for evaluation displays but never enters inference.
- LLM output is structurally validated and wrapped with application-owned
  decision fields.
- Score persistence uses a process-local lock, file synchronization, and atomic
  replacement.
- Anonymous write endpoints are rate-limited per backend process.
- Localhost development accepts numeric ports while production CORS remains
  restricted to this project's Vercel domains.
- Gateway transport mode is normalized to public provider mode `live`; `demo`
  remains explicit in every response and UI badge.

## System boundaries

- The source represents a single reporting-period sample and has no event
  timestamps, account identities, or unstructured historical communications.
  Date filtering, temporal claims, and account-level journeys are therefore not
  part of the application contract.
- Inquiry text is supplied by the user and stored separately from the source
  dataset with record and checksum binding.
- Jev outputs are probabilistic semantic judgments, not conversion
  probabilities. Confidence and uncertainty remain visible, and deterministic
  application policy owns the resulting workflow action.
- Workflow state, history, confirmation tokens, and semantic cache entries are
  stored transactionally in SQLite. Score results use a versioned, input-hashed
  atomic JSON cache.
- Actions remain inside the application; automated customer outreach is
  disabled for every route.
