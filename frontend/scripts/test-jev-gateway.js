const fs = require('fs');
const path = require('path');

const loadLocalGatewayKey = () => {
  if (process.env.AI_GATEWAY_API_KEY) return;
  const envPath = path.join(__dirname, '..', '.env.local');
  if (!fs.existsSync(envPath)) return;
  const line = fs.readFileSync(envPath, 'utf8')
    .split(/\r?\n/)
    .find((value) => /^\s*AI_GATEWAY_API_KEY\s*=/.test(value));
  if (!line) return;
  const value = line.replace(/^\s*AI_GATEWAY_API_KEY\s*=\s*/, '').trim().replace(/^['"]|['"]$/g, '');
  if (value && !value.startsWith('your_')) process.env.AI_GATEWAY_API_KEY = value;
};

const main = async () => {
  loadLocalGatewayKey();
  if (!process.env.AI_GATEWAY_API_KEY) {
    console.error('AI_GATEWAY_API_KEY is not set. Add it to frontend/.env.local (ignored by git) or export it for this command.');
    process.exitCode = 2;
    return;
  }
  const { experimental_evaluate: evaluate } = await import('ai');
  const catalogProductTaxonomy = {
    'Car Accessories': [
      'Batteries & Accessories',
      'Exterior Accessories',
      'Garage & Car Care',
      'Interior Accessories',
      'Replacement Parts',
      'Towing & Hitches',
    ],
    'Car Electronics': ['Car Electronics'],
    'Performance & Non-auto': ['Motorcycle Parts', 'Performance Parts', 'Shelters & RV'],
    'Tires & Wheels': ['Tires & Wheels'],
  };
  const inquiryResult = await evaluate({
    model: 'typesafe-ai/jev',
    state: {
      inquiry: 'Please quote 200 replacement batteries; we need delivery next month.',
      catalog_product_taxonomy: catalogProductTaxonomy,
    },
    questions: {
      intent: {
        type: 'choice',
        instructions: 'What is the main customer intent?',
        criteria: {
          quote_request: 'Requests pricing or a concrete purchase.',
          research: 'Explores or compares without a current order.',
          support: 'Reports a defect or service issue.',
          other: 'Anything else.',
        },
      },
      product_interest: {
        type: 'choice',
        instructions: 'Which top-level catalog product group best matches the product in the inquiry? Use the subgroup hierarchy as the authoritative catalog semantics.',
        criteria: {
          car_accessories: 'Car Accessories. Includes Batteries & Accessories, Exterior Accessories, Garage & Car Care, Interior Accessories, Replacement Parts, and Towing & Hitches.',
          car_electronics: 'Car Electronics. Includes the Car Electronics subgroup.',
          performance_non_auto: 'Performance & Non-auto. Includes Motorcycle Parts, Performance Parts, and Shelters & RV.',
          tires_wheels: 'Tires & Wheels. Includes the Tires & Wheels subgroup.',
          unknown: 'The inquiry does not identify a product represented by the catalog.',
        },
      },
      urgent: {
        type: 'boolean',
        instructions: 'Does the inquiry explicitly express urgency or time sensitivity?',
      },
      human_review_required: {
        type: 'boolean',
        instructions: 'Does this inquiry require human review because its operational intent is ambiguous, internally conflicting, unsupported, or safety-sensitive? Routine missing qualification details alone are not sufficient.',
      },
      escalation_reason: {
        type: 'choice',
        instructions: 'What is the primary reason for human escalation, if any?',
        criteria: {
          none: 'The request can be handled by an approved workflow queue.',
          ambiguous_intent: 'The primary intent is too ambiguous to route safely.',
          conflicting_signals: 'The request contains conflicting operational intents.',
          unsupported_request: 'The request is outside the approved workflow queues.',
          safety_sensitive: 'The request needs a person because of safety or operational risk.',
        },
      },
    },
    maxRetries: 2,
    abortSignal: AbortSignal.timeout(15000),
  });
  const commandResult = await evaluate({
    model: 'typesafe-ai/jev',
    state: {
      command: 'Mark the selected inquiry as reviewed.',
      selected_inquiry_count: 1,
    },
    questions: {
      tool: {
        type: 'choice',
        instructions: 'Which approved application tool best matches the user request?',
        criteria: {
          list_opportunities: 'Retrieve opportunities using supported filters.',
          show_action_queue: 'Show inquiry workflow queues and statuses.',
          score_opportunities: 'Run calibrated ML scoring for selected records.',
          explain_opportunity: 'Explain one existing opportunity score.',
          summarize_portfolio: 'Compute an approved portfolio aggregation.',
          update_workflow_status: 'Preview a workflow status change for inquiries.',
          unknown: 'The request is unsupported or too unclear.',
        },
      },
      workflow_status: {
        type: 'choice',
        instructions: 'Which workflow status did the user request?',
        criteria: {
          new: 'New',
          in_review: 'In review',
          reviewed: 'Reviewed',
          resolved: 'Resolved',
          not_specified: 'No workflow status was requested.',
        },
      },
      requested_effect: {
        type: 'choice',
        instructions: 'Does the user request a read-only operation or a persisted workflow state change?',
        criteria: {
          read_only: 'Only reads, scores, explains, or summarizes existing data.',
          state_change: 'Changes persisted workflow state.',
          unclear: 'It is unclear whether the request reads or changes data.',
        },
      },
      confirmation_sensitivity: {
        type: 'boolean',
        instructions: 'Would fulfilling this request change persisted workflow data or require explicit confirmation?',
      },
    },
    maxRetries: 2,
    abortSignal: AbortSignal.timeout(15000),
  });
  const intent = inquiryResult.answers.intent;
  const productInterest = inquiryResult.answers.product_interest;
  const urgent = inquiryResult.answers.urgent;
  const humanReview = inquiryResult.answers.human_review_required;
  const escalationReason = inquiryResult.answers.escalation_reason;
  console.log(JSON.stringify({
    ok: true,
    model: inquiryResult.response.modelId,
    inquiry: {
      intent: intent.choice,
      intent_probabilities: intent.probabilities,
      product_interest: productInterest.choice,
      product_probabilities: productInterest.probabilities,
      urgency_probability: urgent.probability,
      human_review_probability: humanReview.probability,
      escalation_reason: escalationReason.choice,
      escalation_reason_probabilities: escalationReason.probabilities,
      usage: inquiryResult.usage,
    },
    command: {
      tool: commandResult.answers.tool.choice,
      workflow_status: commandResult.answers.workflow_status.choice,
      requested_effect: commandResult.answers.requested_effect.choice,
      confirmation_sensitivity: commandResult.answers.confirmation_sensitivity.probability,
      usage: commandResult.usage,
    },
  }, null, 2));
};

main().catch((error) => {
  console.error(`Gateway Jev smoke test failed: ${error.message || 'unknown error'}`);
  process.exitCode = 1;
});
