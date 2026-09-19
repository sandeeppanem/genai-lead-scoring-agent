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
  const result = await evaluate({
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
    },
    maxRetries: 2,
    abortSignal: AbortSignal.timeout(15000),
  });
  const intent = result.answers.intent;
  const productInterest = result.answers.product_interest;
  const urgent = result.answers.urgent;
  console.log(JSON.stringify({
    ok: true,
    model: result.response.modelId,
    intent: intent.choice,
    intent_probabilities: intent.probabilities,
    product_interest: productInterest.choice,
    product_probabilities: productInterest.probabilities,
    urgency_probability: urgent.probability,
    usage: result.usage,
  }, null, 2));
};

main().catch((error) => {
  console.error(`Gateway Jev smoke test failed: ${error.message || 'unknown error'}`);
  process.exitCode = 1;
});
