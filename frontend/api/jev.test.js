const test = require('node:test');
const assert = require('node:assert/strict');

const { distributionConfidence, normalizeAnswers, validateQuestions } = require('./jev')._test;

test('normalizes Gateway boolean answers into TypeSafe Noul shape', () => {
  const result = normalizeAnswers({ urgent: { type: 'boolean', probability: 0.91 } });
  assert.deepEqual(result, { urgent: { type: 'noul', noul: 0.91 } });
});

test('adds an explicit application-computed confidence to choice answers', () => {
  const result = normalizeAnswers({
    intent: {
      type: 'choice',
      choice: 'support',
      probabilities: { support: 0.9, sales: 0.1 },
    },
  });
  assert.equal(result.intent.choice, 'support');
  assert.equal(result.intent.confidence_source, 'normalized_entropy');
  assert.ok(result.intent.confidence > 0.5);
});

test('validates and converts direct TypeSafe Noul questions for Gateway', () => {
  const result = validateQuestions({
    urgent: { type: 'noul', instructions: 'Is the inquiry urgent?' },
    intent: {
      type: 'choice',
      instructions: 'Choose the intent.',
      criteria: { quote: null, support: null, other: null },
    },
  });
  assert.equal(result.urgent.type, 'boolean');
  assert.equal(result.intent.type, 'choice');
});

test('rejects unbounded question batches', () => {
  const questions = Object.fromEntries(
    Array.from({ length: 13 }, (_, index) => [
      `question_${index}`,
      { type: 'noul', instructions: 'Is this true?' },
    ]),
  );
  assert.throws(() => validateQuestions(questions), /between 1 and 12/);
});

test('confidence is high for peaked distributions and low for flat ones', () => {
  assert.ok(distributionConfidence({ a: 0.99, b: 0.01 }) > 0.9);
  assert.ok(distributionConfidence({ a: 0.5, b: 0.5 }) < 0.01);
});
