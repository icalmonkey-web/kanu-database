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

CANDIDATE_MODELS = [
    "gemini-2.5-flash",
    "gemini-3.5-flash",
    "gemini-1.5-flash"
]

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

def normalize_card_name(name):
    """
    卡片名稱正規化：
    移除空格、英文字母轉大寫、去除後綴字（信用卡、卡、御璽卡、鈦金卡、白金卡），
    確保 'CUBE 卡' 與 'CUBE信用卡' 視為同一個識別 Key。
    """
    if not name:
        return ""
    n = re.sub(r"\s+", "", name).upper()
    n = re.sub(r"(信用卡|御璽卡|鈦金卡|晶緻卡|無限卡|白金卡|卡)$", "", n)
    return n

def fetch_content(target_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    try:
        jina_url = f"https://r.jina.ai/{target_url}"
        res = requests.get(jina_url, headers=headers, timeout=25)
        if res.status_code == 200 and len(res.text.strip()) > 300:
            return res.text
    except Exception:
        pass

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
      "needReg": false,
      "regDeadline": "2026/12/31",
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
    data = {
        "version": "2026.09.20-v0",
        "cards": [],
        "rules": [],
        "commonExclusions": [
            {"keywords": ["全聯", "pxmart"], "message": "全聯福利中心多數信用卡列為非一般消費，不給予一般回饋。"},
            {"keywords": ["7-11", "全家", "超商", "便利商店"], "message": "超商實體刷卡多數排除一般回饋，建議改用指定行動支付綁定。"}
        ]
    }

    # 以「正規化後的銀行+卡名」為唯一 Key 進行去重
    cards_dict = {}
    rules_dict = {}

    for portal in BANK_PORTALS:
        print(f"開始抓取: {portal['bank']}...")
        text = fetch_content(portal["url"])
        if not text:
            continue
        res = parse_bank_data(portal["bank"], text)
        if not res:
            continue

        # ID 映射表，將爬出的舊 ID 導向標準卡片 ID
        id_map = {}

        for c in res.get("cards", []):
            raw_name = c.get("cardName", "").strip()
            if not raw_name:
                continue
            norm_key = f"{portal['bank']}_{normalize_card_name(raw_name)}"
            
            # 若已存在相似卡片，保留更精準的資訊並複用其 ID
            if norm_key not in cards_dict:
                std_id = f"card_{portal['bank']}_{len(cards_dict) + 1}"
                c["id"] = std_id
                cards_dict[norm_key] = c
            id_map[c.get("id")] = cards_dict[norm_key]["id"]
            print(f"  + 卡片收錄/去重整合: {cards_dict[norm_key]['cardName']}")

        for r in res.get("rules", []):
            title = r.get("title", "").strip()
            if not title:
                continue
            # 更新規則指向的 cardId
            if r.get("cardId") in id_map:
                r["cardId"] = id_map[r["cardId"]]
            
            rule_key = f"{r.get('cardId')}_{title}"
            rules_dict[rule_key] = r
            print(f"  + 規則收錄: {title}")

    data["cards"] = list(cards_dict.values())
    data["rules"] = list(rules_dict.values())
    data["version"] = datetime.utcnow().strftime("%Y.%m.%d-v%H%M%S")
    data["lastUpdated"] = datetime.utcnow().isoformat() + "Z"

    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n[完成] data.json 淨化完成！去重後總卡片數: {len(data['cards'])}, 總規則數: {len(data['rules'])}")

if __name__ == "__main__":
    main()
