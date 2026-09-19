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

# 2. 監控入口：同時包含「卡片權益頁」與「銀行活動登錄專區」
BANK_PORTALS = [
    # --- 卡片核心權益 ---
    {
        "bank": "國泰世華",
        "type": "card",
        "url": "https://www.cathaybk.com.tw/cathaybk/personal/product/credit-card/cards/cube/"
    },
    {
        "bank": "玉山銀行",
        "type": "card",
        "url": "https://www.esunbank.com/zh-tw/personal/credit-card/intro/bank-card/u-bear"
    },
    # --- 銀行限時登錄加碼活動區 ---
    {
        "bank": "國泰世華",
        "type": "promo",
        "url": "https://www.cathaybk.com.tw/cathaybk/personal/event/overview/"
    },
    {
        "bank": "玉山銀行",
        "type": "promo",
        "url": "https://www.esunbank.com/zh-tw/personal/credit-card/discount/shops"
    },
    {
        "bank": "台新銀行",
        "type": "promo",
        "url": "https://www.taishinbank.com.tw/TSB/personal/credit/intro/overview/cg021/card001/"
    }
]

def normalize_card_name(name):
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
            return clean_html[:12000]
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

def parse_bank_data(bank_name, content, portal_type):
    prompt = f"""
你現在是專業信用卡分析師。請分析以下【{bank_name}】的網頁文字（頁面性質：{portal_type}）。
請提取有效信用卡卡片資訊，特別是「需要登錄的加碼活動（如滿額贈、指定通路加碼、限額登錄活動）」以及「一般回饋權益」。

嚴格輸出 JSON 格式如下：
{{
  "cards": [
    {{
      "id": "英數唯一識別碼",
      "bank": "{bank_name}",
      "cardName": "信用卡名稱",
      "themeBg": "linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)",
      "textColor": "#ffffff",
      "descTag": "精選回饋特色(10字內)"
    }}
  ],
  "rules": [
    {{
      "id": "規則唯一識別碼",
      "cardId": "對應卡片id(若為全行卡片適用登錄活動可填 bank_all)",
      "title": "活動名稱(如: 蝦皮滿千登錄送10%、日本實體消費登錄加碼5%)",
      "category": "適用通路關鍵字(請展開常用搜尋詞，如: 蝦皮, 網購, 日本, 餐廳, 加油)",
      "baseRate": 1.0,
      "promoRate": 3.0,
      "capAmount": 500,
      "needReg": true,
      "regDeadline": "登錄時間或活動截止日(如: 2026/10/31 或 每月10號 10:00)",
      "quotaInfo": "登錄名額或條件(如: 限量3,000名、需滿 NT$3,000)",
      "regUrl": "活動網址或登錄按鈕連結",
      "excludedKeywords": ["全聯", "7-11", "全家", "水電費", "繳稅"]
    }}
  ]
}}
重要提取原則：
1. 若頁面中有提到「登錄」、「限量」、「加碼」、「名額」，請務必將 needReg 設為 true！
2. 數值（baseRate, promoRate, capAmount）請填數字或 null。
3. 只回傳合法純 JSON，絕不包含 ```json 或 markdown 解說。

網頁內容如下：
{content[:8000]}
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

    cards_dict = {}
    rules_dict = {}

    for portal in BANK_PORTALS:
        print(f"開始抓取: {portal['bank']} ({portal['type']})...")
        text = fetch_content(portal["url"])
        if not text:
            continue
        res = parse_bank_data(portal["bank"], text, portal["type"])
        if not res:
            continue

        id_map = {}
        for c in res.get("cards", []):
            raw_name = c.get("cardName", "").strip()
            if not raw_name:
                continue
            norm_key = f"{portal['bank']}_{normalize_card_name(raw_name)}"
            if norm_key not in cards_dict:
                std_id = f"card_{portal['bank']}_{len(cards_dict) + 1}"
                c["id"] = std_id
                cards_dict[norm_key] = c
            id_map[c.get("id")] = cards_dict[norm_key]["id"]

        for r in res.get("rules", []):
            title = r.get("title", "").strip()
            if not title:
                continue
            if r.get("cardId") in id_map:
                r["cardId"] = id_map[r["cardId"]]
            
            rule_key = f"{r.get('cardId')}_{title}"
            rules_dict[rule_key] = r
            if r.get("needReg"):
                print(f"  🔥 成功捕獲登錄活動: 【{portal['bank']}】{title} (截止/時間: {r.get('regDeadline')})")
            else:
                print(f"  + 常規回饋規則: {title}")

    data["cards"] = list(cards_dict.values())
    data["rules"] = list(rules_dict.values())
    data["version"] = datetime.utcnow().strftime("%Y.%m.%d-v%H%M%S")
    data["lastUpdated"] = datetime.utcnow().isoformat() + "Z"

    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    total_reg = sum(1 for r in data["rules"] if r.get("needReg"))
    print(f"\n[完成] data.json 產出成功！總卡片數: {len(data['cards'])}, 總規則數: {len(data['rules'])}, 其中需要登錄活動數: {total_reg}")

if __name__ == "__main__":
    main()
