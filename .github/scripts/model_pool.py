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

        # 使用您指定的完整模型清單，依穩定度與速度排序輪替
        custom_list = [
            'gemini-3.8-flash',
            'gemini-3.7-flash',
            'gemini-3.6-flash',
            'gemini-3.5-flash',
            'gemini-3.5-flash-lite',
            'gemini-3-flash-preview',
            'gemini-3.1-flash-lite',
            'gemini-2.5-flash-lite',
            'gemini-3.1-flash-live-preview'
        ]

        preferred_models = [n.strip().removeprefix('models/') for n in preferred if n.strip()]
        self.names = list(dict.fromkeys(preferred_models + custom_list))
        self.log('Model rotation: ' + ', '.join(self.names))

    def generate(self, prompt):
        for name in self.names:
            # 已被判定當日額度耗盡或無效的模型跳過
            if name in self.disabled:
                continue

            # 冷卻時間未過跳過
            if self.cooldowns.get(name, 0) > self.clock():
                continue

            # 針對特定模型重試最多 2 次
            for attempt in range(2):
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
                    ):
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

                    # 503 伺服器忙碌或瞬間頻率超標（429 RPM）：短暫退避 2.5 秒重試
                    elif code in ('503', '429'):
                        time.sleep(2.5 * (attempt + 1))
                        continue

                    # JSON 解構失敗或其他伺服器錯誤：冷卻 10 秒後切換下個模型
                    else:
                        self.cooldowns[name] = self.clock() + 10
                        self.log(f'AI switch: {name}, {type(exc).__name__}, code={code or "none"}; cooling down')
                        break

        self.log('No model succeeded for this page; leave it uncached for retry.')
        return None
