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

        # 明確指定目前穩定、支援純文字 JSON 結構化的 Flash / Lite 模型
        # 完全剔除已失效的 2.5 系列，以及 transcribe(語音)、pro(大型) 等型號
        candidate_list = [
            'gemini-3.8-flash',
            'gemini-3.7-flash',
            'gemini-3.6-flash',
            'gemini-3.5-flash',
            'gemini-3.5-flash-lite',
            'gemini-3-flash-preview',
            'gemini-3.1-flash-lite',
            'gemini-3.1-flash-live-preview',
            'gemini-2.5-flash-lite'

        ]

        preferred_models = [n.strip().removeprefix('models/') for n in preferred if n.strip()]
        # 整合外部設定與預設序列，並去除重複項
        self.names = list(dict.fromkeys(preferred_models + candidate_list))
        self.log('Model rotation: ' + ', '.join(self.names))

    def generate(self, prompt):
        for name in self.names:
            if name in self.disabled or self.cooldowns.get(name, 0) > self.clock():
                continue
            try:
                self.requests += 1
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
                elif code in ('429', '503'):
                    # 遇到頻率限制或伺服器暫時忙碌，改為短暫退避重試，不再鎖定 60 秒
                    self.cooldowns[name] = self.clock() + 5
                    reason = 'temporary load/rate limit; retry soon'
                else:
                    self.cooldowns[name] = self.clock() + 15
                    reason = 'request/JSON failed; cooling down'
                self.log(f'AI switch: {name}, {type(exc).__name__}, code={code or "none"}, {reason}')
        self.log('No model succeeded for this page; leave it uncached for retry.')
        return None
