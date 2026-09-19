import os
import json
import re
from datetime import datetime
import requests
from google import genai

# 1. 初始化最新 Gemini Client
api_key = os.environ.get("GEMINI_API_KEY", "")
if not api_key:
    raise ValueError("GEMINI_API_KEY is not set in environment secrets!")

client = genai.Client(api_key=api_key)

# 優先順序：使用最新世代模型，遇不支援自動平滑向下備援
CANDIDATE_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-2.5-flash"
]

# 2. 監控的銀行入口（使用卡片權益具體頁面，資訊充沛）
BANK_PORTALS = [
    {
        "bank": "國泰世華",
        "url": "https://www.cathaybk.com.tw/cathaybk/personal/product/credit-card/cards/cube/"
    },
    {
        "bank": "玉山銀行",
        "url": "https://www.esunbank.com/zh-tw/personal/credit-card/intro/bank-card/u-bear"
    }
]

def fetch_content(target_url):
    """優先透過 Jina Reader 轉為 Markdown，若失敗則直連抓取"""
    jina_url = f"https://r.jina.ai/{target_url}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,text/plain"
    }
    
    # 嘗試 1: Jina Reader
    try:
        print(f"--> [嘗試 Jina] 抓取網址: {jina_url}")
        res = requests.get(jina_url, headers=headers, timeout=25)
        print(f"--> Jina 回應狀態碼: {res.status_code}, 字元數: {len(res.text)}")
        if res.status_code == 200 and len(res.text.strip()) > 150:
            return res.text
    except Exception as e:
        print(f"--> Jina 連線失敗: {e}")

    # 嘗試 2: 直連網址備援
    try:
        print(f"--> [備援直連] 抓取原始網頁: {target_url}")
        res = requests.get(target_url, headers=headers, timeout=20)
        print(f"--> 直連回應狀態碼: {res.status_code}, 字元數: {len(res.text)}")
        if res.status_code == 200:
            # 移除常見 script 與 style 標籤以減輕 token
            clean_html = re.sub(r"<(script|style).*?</\1>", "", res.text, flags=re.DOTALL | re.IGNORECASE)
            return clean_html[:10000]
    except Exception as e:
        print(f"--> 直連抓取失敗: {e}")

    return ""

def call_gemini_with_fallback(prompt):
    """依序嘗試最新模型"""
    for model_name in CANDIDATE_MODELS:
        try:
            print(f"--> 嘗試使用模型: {model_name}...")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            if response and response.text:
                print(f"--> [成功] {model_name} 完成解析！")
                return response.text
        except Exception as err:
            print(f"--> 模型 {model_name} 呼叫未成功: {err}")
            continue
    print("--> 警告：所有備選模型皆嘗試失敗。")
    return None

def parse_with_ai(bank_name, raw_content):
    prompt = f"""
你現在是專業信用卡分析師。請分析以下【{bank_name}】的網頁文字內容。
請提取卡片資訊、各通路回饋趴數、上限與排除通路，並嚴格依照下列 JSON 格式輸出：
{{
  "cards": [
    {{
      "id": "card_{bank_name}_01",
      "bank": "{bank_name}",
      "cardName": "信用卡全名",
      "themeBg": "linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)",
      "textColor": "#ffffff",
      "descTag": "精選最高回饋特色"
    }}
  ],
  "rules": [
    {{
      "id": "rule_{bank_name}_01",
      "cardId": "card_{bank_name}_01",
      "title": "活動或權益名稱",
      "category": "適用通路關鍵字(請展開常見同義詞，用逗號隔開)",
      "baseRate": 1.0,
      "promoRate": 2.0,
      "capAmount": 500,
      "needReg": false,
      "regDeadline": "2026/12/31",
      "excludedKeywords": ["全聯", "7-11", "全家", "水電費", "繳稅", "學費"]
    }}
  ]
}}
要求：
1. baseRate, promoRate, capAmount 必須為純數字或 null。
2. 條款中載明不回饋的項目放入 excludedKeywords。
3. 只回傳純 JSON 字串，絕不夾帶任何 markdown 標籤。

網頁內容如下：
{raw_content[:6000]}
"""
    raw_response = call_gemini_with_fallback(prompt)
    if not raw_response:
        return None

    try:
        text = raw_response.strip()
        text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return json.loads(text.strip())
    except Exception as e:
        print(f"AI JSON 解析失敗 ({bank_name}): {e}")
        return None

def main():
    db_path = "data.json"
    data = {"version": "2026.09.20-v0", "cards": [], "rules": [], "commonExclusions": []}

    if os.path.exists(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"成功讀取既有 data.json，目前卡片數: {len(data.get('cards', []))}")
        except Exception as e:
            print(f"讀取既有 data.json 失敗: {e}")

    cards_map = {c["id"]: c for c in data.get("cards", [])}
    rules_map = {r["id"]: r for r in data.get("rules", [])}

    for portal in BANK_PORTALS:
        print(f"\n==============================")
        print(f"開始抓取: {portal['bank']}")
        raw_text = fetch_content(portal["url"])
        if not raw_text:
            print(f"跳過 {portal['bank']}（未取得有效內容）")
            continue

        result = parse_with_ai(portal["bank"], raw_text)
        if not result:
            print(f"跳過 {portal['bank']}（AI 解析無結果）")
            continue

        for card in result.get("cards", []):
            if card.get("id"):
                cards_map[card["id"]] = card
                print(f"-> 成功寫入卡片: {card.get('cardName')}")

        for rule in result.get("rules", []):
            if rule.get("id"):
                rules_map[rule["id"]] = rule
                print(f"-> 成功寫入權益規則: {rule.get('title')}")

    data["cards"] = list(cards_map.values())
    data["rules"] = list(rules_map.values())

    # 強制產生新版本號，確保寫入與觸發 Commit
    data["version"] = datetime.utcnow().strftime("%Y.%m.%d-v%H%M%S")
    data["lastUpdated"] = datetime.utcnow().isoformat() + "Z"

    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n[完成] data.json 更新成功！新版本號: {data['version']}")
    print(f"目前總卡片數: {len(data['cards'])}, 總規則數: {len(data['rules'])}")

if __name__ == "__main__":
    main()
