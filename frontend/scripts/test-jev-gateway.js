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
  const result = await evaluate({
    model: 'typesafe-ai/jev',
    state: {
      inquiry: 'Please quote 200 replacement batteries; we need delivery next month.',
      catalog: ['Car Accessories', 'Car Electronics', 'Performance & Non-auto', 'Tires & Wheels'],
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
      urgent: {
        type: 'boolean',
        instructions: 'Does the inquiry explicitly express urgency or time sensitivity?',
      },
    },
    maxRetries: 2,
    abortSignal: AbortSignal.timeout(15000),
  });
  const intent = result.answers.intent;
  const urgent = result.answers.urgent;
  console.log(JSON.stringify({
    ok: true,
    model: result.response.modelId,
    intent: intent.choice,
    intent_probabilities: intent.probabilities,
    urgency_probability: urgent.probability,
    usage: result.usage,
  }, null, 2));
};

main().catch((error) => {
  console.error(`Gateway Jev smoke test failed: ${error.message || 'unknown error'}`);
  process.exitCode = 1;
});
