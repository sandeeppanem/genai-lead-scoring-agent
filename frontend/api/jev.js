const crypto = require('crypto');
const { experimental_evaluate: evaluate } = require('ai');

const MODEL = 'typesafe-ai/jev';
const MAX_STATE_BYTES = 20000;
const MAX_QUESTIONS = 12;

const safeEqual = (left, right) => {
  const leftBuffer = Buffer.from(left || '');
  const rightBuffer = Buffer.from(right || '');
  return leftBuffer.length === rightBuffer.length
    && crypto.timingSafeEqual(leftBuffer, rightBuffer);
};

const validateQuestions = (questions) => {
  if (!questions || typeof questions !== 'object' || Array.isArray(questions)) {
    throw new Error('questions must be an object');
  }
  const entries = Object.entries(questions);
  if (!entries.length || entries.length > MAX_QUESTIONS) {
    throw new Error(`questions must contain between 1 and ${MAX_QUESTIONS} entries`);
  }
  return Object.fromEntries(entries.map(([id, question]) => {
    if (!/^[a-z][a-z0-9_]{0,63}$/i.test(id)) {
      throw new Error(`invalid question id: ${id}`);
    }
    if (!question || typeof question !== 'object') {
      throw new Error(`invalid question: ${id}`);
    }
    if (typeof question.instructions !== 'string'
      || question.instructions.length < 3
      || question.instructions.length > 1000) {
      throw new Error(`invalid instructions: ${id}`);
    }
    const type = question.type === 'noul' ? 'boolean' : question.type;
    if (!['boolean', 'choice', 'score'].includes(type)) {
      throw new Error(`unsupported question type: ${question.type}`);
    }
    if (type === 'choice') {
      const criteria = question.criteria;
      if (!criteria || typeof criteria !== 'object' || Array.isArray(criteria)) {
        throw new Error(`choice criteria required: ${id}`);
      }
      const optionCount = Object.keys(criteria).length;
      if (optionCount < 2 || optionCount > 30) {
        throw new Error(`choice criteria must contain 2-30 options: ${id}`);
      }
    }
    if (type === 'score' && (!Array.isArray(question.criteria)
      || question.criteria.length < 2
      || question.criteria.length > 20)) {
      throw new Error(`score criteria must contain 2-20 levels: ${id}`);
    }
    return [id, { ...question, type }];
  }));
};

const distributionConfidence = (probabilities) => {
  const values = Object.values(probabilities || {}).map(Number);
  if (values.length < 2 || values.some((value) => !Number.isFinite(value) || value < 0)) {
    throw new Error('evaluation response omitted a valid probability distribution');
  }
  const total = values.reduce((sum, value) => sum + value, 0);
  if (total <= 0) throw new Error('evaluation response contained an empty distribution');
  const normalized = values.map((value) => value / total);
  const entropy = -normalized.reduce(
    (sum, value) => sum + (value > 0 ? value * Math.log(value) : 0),
    0,
  );
  return Math.max(0, Math.min(1, 1 - (entropy / Math.log(values.length))));
};

const normalizeAnswers = (answers) => Object.fromEntries(
  Object.entries(answers).map(([id, answer]) => {
    if (answer.type === 'boolean') {
      return [id, { type: 'noul', noul: answer.probability }];
    }
    if (answer.type === 'choice') {
      return [id, {
        type: 'choice',
        choice: answer.choice,
        probabilities: answer.probabilities,
        confidence: distributionConfidence(answer.probabilities),
        confidence_source: 'normalized_entropy',
      }];
    }
    return [id, {
      type: 'score',
      score: answer.score,
      probabilities: answer.probabilities,
      confidence: distributionConfidence(answer.probabilities),
      confidence_source: 'normalized_entropy',
    }];
  }),
);

module.exports = async function handler(request, response) {
  if (request.method !== 'POST') {
    response.setHeader('Allow', 'POST');
    return response.status(405).json({ error: 'Method not allowed' });
  }
  const expectedToken = process.env.JEV_ADAPTER_TOKEN || '';
  const suppliedToken = String(request.headers.authorization || '').replace(/^Bearer\s+/i, '');
  if (!expectedToken || !safeEqual(suppliedToken, expectedToken)) {
    return response.status(401).json({ error: 'Unauthorized' });
  }
  if (!process.env.AI_GATEWAY_API_KEY) {
    return response.status(503).json({ error: 'AI Gateway is not configured' });
  }

  try {
    const body = typeof request.body === 'string' ? JSON.parse(request.body) : request.body;
    if (!body || body.state === undefined) throw new Error('state is required');
    if (Buffer.byteLength(JSON.stringify(body.state), 'utf8') > MAX_STATE_BYTES) {
      throw new Error('state exceeds the 20 KB limit');
    }
    const questions = validateQuestions(body.questions);
    const result = await evaluate({
      model: MODEL,
      state: body.state,
      questions,
      maxRetries: 2,
      abortSignal: AbortSignal.timeout(15000),
    });
    return response.status(200).json({
      model: result.response.modelId || MODEL,
      answers: normalizeAnswers(result.answers),
      usage: {
        input_tokens: result.usage.inputTokens || 0,
        output_tokens: result.usage.outputTokens || 0,
      },
    });
  } catch (error) {
    const validationError = error instanceof SyntaxError
      || String(error.message || '').startsWith('invalid')
      || String(error.message || '').includes('required')
      || String(error.message || '').includes('must contain')
      || String(error.message || '').includes('exceeds')
      || String(error.message || '').includes('unsupported');
    return response.status(validationError ? 400 : 502).json({
      error: validationError
        ? String(error.message)
        : 'The Jev evaluation provider is temporarily unavailable.',
    });
  }
};

module.exports._test = { distributionConfidence, normalizeAnswers, validateQuestions };
