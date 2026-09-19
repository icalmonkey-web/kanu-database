import os
import json
import re
from datetime import datetime
import requests
from google import genai

# 1. 初始化 Gemini Client
api_key = os.environ.get("GEMINI_API_KEY", "")
if not api_key:
    raise ValueError("GEMINI_API_KEY is not set!")

client = genai.Client(api_key=api_key)

# 優先順序：使用穩定高效模型
CANDIDATE_MODELS = [
    "gemini-2.5-flash",
    "gemini-3.5-flash",
    "gemini-1.5-flash"
]

# 擴充為全市場熱門神卡入口（國泰、玉山、台新、富邦、聯邦）
BANK_PORTALS = [
    {
        "bank": "國泰世華",
        "url": "https://www.cathaybk.com.tw/cathaybk/personal/product/credit-card/cards/cube/"
    },
    {
        "bank": "玉山銀行",
        "url": "https://www.esunbank.com/zh-tw/personal/credit-card/intro/bank-card/u-bear"
    },
    {
        "bank": "台新銀行",
        "url": "https://www.taishinbank.com.tw/TSB/personal/credit/intro/overview/cg021/card001/"
    },
    {
        "bank": "台北富邦",
        "url": "https://www.fubon.com/banking/personal/credit_card/all_card/costco/costco.htm"
    }
]

def fetch_content(target_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    # 優先嘗試 Jina Reader 轉換為純文字
    try:
        jina_url = f"https://r.jina.ai/{target_url}"
        res = requests.get(jina_url, headers=headers, timeout=25)
        if res.status_code == 200 and len(res.text.strip()) > 300:
            return res.text
    except Exception:
        pass

    # 備援直連抓取
    try:
        res = requests.get(target_url, headers=headers, timeout=20)
        if res.status_code == 200:
            clean_html = re.sub(r"<(script|style).*?</\1>", "", res.text, flags=re.DOTALL | re.IGNORECASE)
            return clean_html[:10000]
    except Exception:
        pass
    return ""

def call_gemini(prompt):
    for model_name in CANDIDATE_MODELS:
        try:
            res = client.models.generate_content(model=model_name, contents=prompt)
            if res and res.text:
                return res.text
        except Exception:
            continue
    return None

def parse_bank_data(bank_name, content):
    prompt = f"""
你現在是專業信用卡專家。請分析以下【{bank_name}】網頁文字，提取此卡片或此頁面多張卡片之資訊、回饋規則、登錄活動與除外條款。
嚴格輸出 JSON 格式如下：
{{
  "cards": [
    {{
      "id": "英數唯一識別碼",
      "bank": "{bank_name}",
      "cardName": "信用卡名稱",
      "themeBg": "linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)",
      "textColor": "#ffffff",
      "descTag": "精選重點回饋描述(10字內)"
    }}
  ],
  "rules": [
    {{
      "id": "規則唯一識別碼",
      "cardId": "對應卡片id",
      "title": "回饋活動名稱",
      "category": "適用通路關鍵字(請擴充常用詞，如: 網購, 街口, momo, 日本, 加油, 餐飲)",
      "baseRate": 1.0,
      "promoRate": 2.0,
      "capAmount": 500,
      "needReg": true或false,
      "regDeadline": "登錄截止日或活動結束日(例如 2026/10/31)",
      "excludedKeywords": ["全聯", "7-11", "全家", "水電費", "學費", "稅款"]
    }}
  ]
}}
要求：
1. 必須是合法 JSON，數值型態為 number 或 null。
2. 若有需要「登錄」的加碼活動，務必將 needReg 標記為 true，並寫入 regDeadline。
3. 絕不夾帶任何 markdown 語法（不要加 ```json）。

內容如下：
{content[:7000]}
"""
    raw = call_gemini(prompt)
    if not raw:
        return None
    try:
        clean = re.sub(r"^```(json)?", "", raw.strip(), flags=re.IGNORECASE)
        clean = re.sub(r"```$", "", clean.strip())
        return json.loads(clean.strip())
    except Exception as e:
        print(f"解析 JSON 失敗 ({bank_name}): {e}")
        return None

def main():
    db_path = "data.json"
    data = {"version": "2026.09.20-v0", "cards": [], "rules": [], "commonExclusions": [
        {"keywords": ["全聯", "pxmart"], "message": "全聯福利中心多數信用卡列為非一般消費，不給予一般回饋。"},
        {"keywords": ["7-11", "全家", "超商", "便利商店"], "message": "超商實體刷卡多數排除一般回饋，建議改用指定行動支付綁定。"}
    ]}

    if os.path.exists(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass

    cards_map = {c["cardName"]: c for c in data.get("cards", [])}
    rules_map = {r["title"]: r for r in data.get("rules", [])}

    for portal in BANK_PORTALS:
        print(f"抓取 {portal['bank']}...")
        text = fetch_content(portal["url"])
        if not text:
            continue
        res = parse_bank_data(portal["bank"], text)
        if not res:
            continue

        for c in res.get("cards", []):
            if c.get("cardName"):
                cards_map[c["cardName"]] = c
                print(f"  + 卡片: {c['cardName']}")

        for r in res.get("rules", []):
            if r.get("title"):
                rules_map[r["title"]] = r
                print(f"  + 規則/登錄: {r['title']}")

    data["cards"] = list(cards_map.values())
    data["rules"] = list(rules_map.values())
    data["version"] = datetime.utcnow().strftime("%Y.%m.%d-v%H%M%S")
    data["lastUpdated"] = datetime.utcnow().isoformat() + "Z"

    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n成功！總卡片數: {len(data['cards'])}, 總規則數: {len(data['rules'])}")

if __name__ == "__main__":
    main()
