"""Discover text models once and fail over without a global request cap."""
import json
import re
import time

class ModelPool:
    def __init__(self, client, preferred=(), clock=time.monotonic, log=print):
        self.client = client
        self.clock = clock
        self.log = log
        self.disabled = set()
        self.cooldowns = {}
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
        preferred_models = [n.strip().removeprefix('models/') for n in preferred if n.strip()]
        names.sort(key=lambda n: ('flash' not in n, 'lite' not in n, n))
        self.names = list(dict.fromkeys([n for n in preferred_models if not names or n in names] + names))
        if not self.names:
            raise RuntimeError('No text models available; check GEMINI_MODELS and API access.')
        self.log('Model rotation: ' + ', '.join(self.names))

    def generate(self, prompt):
        for name in self.names:
            # 已被判定當日額度耗盡或無效的模型跳過
            if name in self.disabled:
                continue

            # 冷卻時間未過跳過
            if self.cooldowns.get(name, 0) > self.clock():
                continue

            # 每個模型每頁只嘗試一次；限流時切換下一個可用模型。
            for attempt in range(1):
                try:
                    self.requests += 1
                    response = self.client.models.generate_content(
                        model=name,
                        contents=prompt
                    )
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

                    # 404 不存在或 400 (不支援純文字/如 live-preview)，直接標記本輪停用，不再浪費時間
                    if code in ('404', '400'):
                        self.disabled.add(name)
                        self.log(f'AI switch: {name}, code={code} (不支援純文字或不存在); disabled for this run')
                        break

                    # 429 且屬於每日額度已滿（PerDay），本輪停用
                    elif code == '429' and re.search(r'PerDay|per day|daily', detail, re.I):
                        self.disabled.add(name)
                        self.log(f'AI switch: {name}, daily quota exhausted; disabled')
                        break

                    # 瞬間頻率超標：依服務建議冷卻，先切換下一個模型。
                    elif code == '429':
                        delay = re.search(r'(?:retryDelay[\s\x27\x22:]+|retry in\s+)([\d.]+)', detail, re.I)
                        self.cooldowns[name] = self.clock() + max(60, float(delay[1]) if delay else 60)
                        break

                    # JSON 解構失敗或其他伺服器錯誤：冷卻 10 秒後切換下個模型
                    else:
                        self.cooldowns[name] = self.clock() + 10
                        self.log(f'AI switch: {name}, {type(exc).__name__}, code={code or "none"}; cooling down')
                        break

        self.log('No model succeeded for this page; leave it uncached for retry.')
        return None
