import unittest
from types import SimpleNamespace as NS
from model_pool import ModelPool


class APIError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class RotationTests(unittest.TestCase):
    def pool(self, outcomes):
        calls = []
        def generate(model, contents):
            calls.append(model)
            outcome = outcomes[model]
            if isinstance(outcome, Exception):
                raise outcome
            return NS(text=outcome)
        models = NS(list=lambda: [NS(name='models/' + n, supported_actions=['generateContent']) for n in outcomes], generate_content=generate)
        return ModelPool(NS(models=models), list(outcomes), clock=lambda: 0, log=lambda x: None), calls

    def test_daily_quota_switch_and_no_repeat(self):
        pool, calls = self.pool({'gemini-a': APIError(429, 'GenerateRequestsPerDayPerProjectPerModel'), 'gemini-b': '{"cards":[],"rules":[]}'})
        for _ in range(22):
            self.assertIsNotNone(pool.generate('page'))
        self.assertEqual(calls.count('gemini-a'), 1)
        self.assertEqual(calls.count('gemini-b'), 22)

    def test_invalid_json_then_missing_model_then_success(self):
        pool, calls = self.pool({'gemini-a': '[]', 'gemini-b': APIError(404, 'missing'), 'gemini-c': '```json\n{"cards":[],"rules":[]}\n```'})
        self.assertIsNotNone(pool.generate('page'))
        self.assertEqual(len(calls), 3)

    def test_minute_limit_cooldown_and_recovery(self):
        pool, calls = self.pool({'gemini-a': APIError(429, 'retry in 90s')})
        self.assertIsNone(pool.generate('page'))
        self.assertIsNone(pool.generate('page'))
        self.assertEqual(len(calls), 1)
        pool.clock = lambda: 91
        pool.generate('page')
        self.assertEqual(len(calls), 2)

    def test_daily_exhaustion_stops_requests(self):
        pool, calls = self.pool({'gemini-a': APIError(429, 'PerDay')})
        self.assertIsNone(pool.generate('page'))
        self.assertIsNone(pool.generate('next'))
        self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main()
