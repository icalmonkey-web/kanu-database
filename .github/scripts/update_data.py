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

# 優先順序：從最新最強的開始嘗試，失敗則自動向下遞補備援
CANDIDATE_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-1.5-flash"
]

# 2. 監控的銀行入口
BANK_PORTALS = [
    {"bank": "國泰世華", "url": "https://www.cathaybk.com.tw/cathaybk/personal/event/overview/"},
    {"bank": "玉山銀行", "url": "https://www.esunbank.com/zh-tw/personal/credit-card/discount/shops"}
]

def fetch_markdown_via_jina(target_url):
    """利用 Jina Reader 免費將網頁轉為 Markdown 文字"""
    jina_url = f"https://r.jina.ai/{target_url}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(jina_url, headers=headers, timeout=25)
        if res.status_code == 200:
            return res.text
    except Exception as e:
        print(f"Fetch failed for {target_url}: {e}")
    return ""

def call_gemini_with_fallback(prompt):
    """依序嘗試最新模型，成功即回傳，失敗則自動順延"""
    for model_name in CANDIDATE_MODELS:
        try:
            print(f"嘗試使用模型: {model_name}...")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            if response and response.text:
                print(f"成功透過 {model_name} 解析內容！")
                return response.text
        except Exception as err:
            print(f"模型 {model_name} 無法使用或回傳錯誤: {err}")
            continue
    print("所有備選模型皆嘗試失敗。")
    return None

def parse_with_ai(bank_name, raw_content):
    """使用 Gemini 解析活動、回饋率與除外條款"""
    if not raw_content or len(raw_content.strip()) < 100:
        return None

    prompt = f"""
你現在是專業信用卡資料庫分析師。請分析以下【{bank_name}】的活動網頁文字內容。
請提取有效信用卡活動，並嚴格依照下列 JSON 格式輸出：
{{
  "cards": [
    {{
      "id": "英數唯一識別碼",
      "bank": "{bank_name}",
      "cardName": "信用卡全名",
      "themeBg": "linear-gradient(135deg, #1c4e36 0%, #297451 100%)",
      "textColor": "#ffffff",
      "descTag": "特色簡述"
    }}
  ],
  "rules": [
    {{
      "id": "規則唯一識別碼",
      "cardId": "對應上方卡片的id",
      "title": "活動或權益簡稱",
      "category": "適用通路關鍵字(請主動擴充常見搜尋同義詞，以逗號分隔)",
      "baseRate": 1.0,
      "promoRate": 2.0,
      "capAmount": 500,
      "needReg": false,
      "regDeadline": "永久或日期",
      "excludedKeywords": ["注意事項中載明排除的所有通路"]
    }}
  ]
}}
注意事項：
1. 數值請輸出純數字（如 3.0，capAmount 若無上限請填 null）。
2. 只輸出純 JSON，不要包含任何 markdown 標記或解說文字。

網頁內容如下：
{raw_content[:5000]}
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
    data = {"version": "2026.09.20-v1", "cards": [], "rules": [], "commonExclusions": []}

    if os.path.exists(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"讀取既有 data.json 失敗: {e}")

    existing_card_names = {c["cardName"] for c in data.get("cards", [])}
    has_updates = False

    for portal in BANK_PORTALS:
        print(f"\n開始抓取 {portal['bank']}...")
        raw_text = fetch_markdown_via_jina(portal["url"])
        if not raw_text:
            continue

        result = parse_with_ai(portal["bank"], raw_text)
        if not result:
            continue

        for card in result.get("cards", []):
            if card.get("cardName") and card["cardName"] not in existing_card_names:
                data.setdefault("cards", []).append(card)
                existing_card_names.add(card["cardName"])
                has_updates = True

        for rule in result.get("rules", []):
            if rule.get("title"):
                data.setdefault("rules", []).append(rule)
                has_updates = True

    if has_updates or not os.path.exists(db_path):
        data["version"] = datetime.utcnow().strftime("%Y.%m.%d-v%H%M")
        data["lastUpdated"] = datetime.utcnow().isoformat() + "Z"
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("\ndata.json 已成功更新版本:", data["version"])
    else:
        print("\n資料無異動，保留既有資料庫。")

if __name__ == "__main__":
    main()
