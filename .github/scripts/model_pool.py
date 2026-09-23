"""Discover text models once and fail over without a global request cap.

models.list reports capabilities, not pricing or remaining quota. Billing and
free-tier availability are controlled by the Google project, not this module.
"""
import json
import re
import time


class ModelPool:
    def __init__(self, client, preferred=(), clock=time.monotonic, log=print):
        self.client, self.clock, self.log = client, clock, log
        self.disabled, self.cooldowns = set(), {}
        self.requests = 0
        names = []
        try:
            for model in client.models.list():
                name = (model.name or '').removeprefix('models/')
                actions = model.supported_actions or []
                if ('generateContent' in actions
                        and name.startswith(('gemini-', 'gemma-'))
                        and not re.search(r'image|audio|tts|live|robotics|embedding|computer-use', name)):
                    names.append(name)
        except Exception as exc:
            self.log(f'Model discovery failed ({type(exc).__name__}); using configured models.')
        preferred = [n.strip().removeprefix('models/') for n in preferred if n.strip()]
        # Prefer economical Flash models, then other supported text models.
        names.sort(key=lambda n: ('flash' not in n, 'lite' not in n, n))
        self.names = list(dict.fromkeys([n for n in preferred if not names or n in names] + names))
        if not self.names:
            raise RuntimeError('No text models available; check GEMINI_MODELS and API access.')
        self.log('Model rotation: ' + ', '.join(self.names))

    def generate(self, prompt):
        for name in self.names:
            if name in self.disabled or self.cooldowns.get(name, 0) > self.clock():
                continue
            try:
                self.requests += 1
                # Plain JSON instruction also supports models without JSON mode.
                response = self.client.models.generate_content(model=name, contents=prompt)
                text = (response.text or '').strip()
                text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text)
                result = json.loads(text)
                if not isinstance(result, dict) or any(
                    not isinstance(result.get(key), list) for key in ('cards', 'rules')
                ) or any(not isinstance(row, dict) for key in ('cards', 'rules') for row in result[key]):
                    raise ValueError('Expected cards/rules arrays of objects')
                self.log(f'AI success: {name}')
                return result
            except Exception as exc:
                code = str(getattr(exc, 'code', ''))
                detail = str(exc)
                if code in ('403', '404') or (code == '429' and re.search(r'PerDay|per day|daily', detail, re.I)):
                    self.disabled.add(name)
                    reason = 'unavailable or daily quota exhausted; disabled for this run'
                elif code == '429':
                    delay = re.search(r'(?:retryDelay[\s\x27\x22:]+|retry in\s+)([\d.]+)', detail, re.I)
                    self.cooldowns[name] = self.clock() + max(60, float(delay[1]) if delay else 60)
                    reason = 'rate limited; cooling down'
                else:
                    self.cooldowns[name] = self.clock() + 60
                    reason = 'request/JSON failed; cooling down'
                self.log(f'AI switch: {name}, {type(exc).__name__}, code={code or "none"}, {reason}')
        self.log('No model succeeded for this page; leave it uncached for retry.')
        return None
