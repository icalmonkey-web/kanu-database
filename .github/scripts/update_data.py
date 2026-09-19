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

# 2. 精選具備豐富文字內容之權益與活動入口
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

# 基準卡片資料（確保資料庫永不縮水，涵蓋主流神卡）
DEFAULT_CARDS = [
    {
        "id": "card_cathay_cube",
        "bank": "國泰世華",
        "cardName": "CUBE卡",
        "themeBg": "linear-gradient(135deg, #1c4e36 0%, #297451 100%)",
        "textColor": "#ffffff",
        "descTag": "精選權益天天切換 3% 無上限"
    },
    {
        "id": "card_esun_ubear",
        "bank": "玉山銀行",
        "cardName": "玉山 U Bear卡",
        "themeBg": "linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)",
        "textColor": "#ffffff",
        "descTag": "網購與行動支付最高 3%"
    },
    {
        "id": "card_taishin_gogo",
        "bank": "台新銀行",
        "cardName": "@GoGo卡",
        "themeBg": "linear-gradient(135deg, #232526 0%, #414345 100%)",
        "textColor": "#ffffff",
        "descTag": "行動支付與指定網購最高 3.8%"
    },
    {
        "id": "card_fubon_costco",
        "bank": "台北富邦",
        "cardName": "富邦 Costco聯名卡",
        "themeBg": "linear-gradient(135deg, #0d324d 0%, #7f5a83 100%)",
        "textColor": "#ffffff",
        "descTag": "Costco 店內 2%、加油最高 3%"
    }
]

# 基準登錄活動（包含限量名額與截止日期）
DEFAULT_RULES = [
    {
        "id": "rule_cube_online",
        "cardId": "card_cathay_cube",
        "title": "玩數位精選網購回饋",
        "category": "網購, 蝦皮, momo, PChome, 酷澎, 博客來",
        "baseRate": 0.3,
        "promoRate": 2.7,
        "capAmount": None,
        "needReg": False,
        "regDeadline": "2026/12/31",
        "excludedKeywords": ["全聯", "7-11", "全家", "繳稅", "水電費", "學費"]
    },
    {
        "id": "rule_cube_japan_reg",
        "cardId": "card_cathay_cube",
        "title": "日本實體消費加碼登錄活動",
        "category": "日本, 國外實體, 海外消費",
        "baseRate": 0.3,
        "promoRate": 4.7,
        "capAmount": 1000,
        "needReg": True,
        "regDeadline": "每月1日 16:00 開放登錄 (限量10,000名)",
        "excludedKeywords": ["網購", "儲值"]
    },
    {
        "id": "rule_ubear_online",
        "cardId": "card_esun_ubear",
        "title": "指定網購與行動支付最高 3%",
        "category": "網購, momo, 蝦皮, LINE Pay, 街口支付",
        "baseRate": 1.0,
        "promoRate": 2.0,
        "capAmount": 200,
        "needReg": False,
        "regDeadline": "2026/12/31",
        "excludedKeywords": ["全聯", "超商", "公用事業代繳"]
    },
    {
        "id": "rule_ubear_sub_reg",
        "cardId": "card_esun_ubear",
        "title": "影音娛樂指定加碼登錄活動",
        "category": "Netflix, Spotify, Disney+, YouTube Premium",
        "baseRate": 1.0,
        "promoRate": 9.0,
        "capAmount": 100,
        "needReg": True,
        "regDeadline": "2026/12/31 前需登錄一次",
        "excludedKeywords": ["非官方直營訂閱"]
    },
    {
        "id": "rule_gogo_digital",
        "cardId": "card_taishin_gogo",
        "title": "指定行動支付與網購 3.8%",
        "category": "LINE Pay, 全盈+PAY, 台新Pay, 網購, 蝦皮",
        "baseRate": 0.5,
        "promoRate": 3.3,
        "capAmount": 1000,
        "needReg": False,
        "regDeadline": "2026/12/31",
        "excludedKeywords": ["全聯", "便利商店", "停車費", "罰鍰"]
    },
    {
        "id": "rule_gogo_fest_reg",
        "cardId": "card_taishin_gogo",
        "title": "Richart 狂歡節限時滿額登錄加碼",
        "category": "百貨, 餐廳, 網購, 旅行社",
        "baseRate": 0.5,
        "promoRate": 5.5,
        "capAmount": 500,
        "needReg": True,
        "regDeadline": "每週三 10:00 限量登錄 (限前2,000名)",
        "excludedKeywords": ["一般消費除外條款"]
    },
    {
        "id": "rule_fubon_costco",
        "cardId": "card_fubon_costco",
        "title": "Costco賣場與線上購物滿額回饋",
        "category": "Costco, 好市多, Costco線上購物, 加油",
        "baseRate": 1.0,
        "promoRate": 2.0,
        "capAmount": None,
        "needReg": False,
        "regDeadline": "2026/12/31",
        "excludedKeywords": ["好市多賣場外非一般消費"]
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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
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
你現在是專業信用卡分析師。請分析以下【{bank_name}】的網頁文字內容。
請提取信用卡資訊與回饋活動（包含常規權益及需要登錄的加碼活動），嚴格依照下列 JSON 格式輸出：
{{
  "cards": [
    {{
      "id": "英數唯一識別碼",
      "bank": "{bank_name}",
      "cardName": "信用卡全名",
      "themeBg": "linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)",
      "textColor": "#ffffff",
      "descTag": "特色簡述"
    }}
  ],
  "rules": [
    {{
      "id": "規則唯一識別碼",
      "cardId": "對應卡片id",
      "title": "回饋活動名稱",
      "category": "適用通路關鍵字(請展開常用詞，如: 網購, 蝦皮, momo, 日本, 餐廳, 加油)",
      "baseRate": 1.0,
      "promoRate": 2.0,
      "capAmount": 500,
      "needReg": true或false,
      "regDeadline": "登錄截止日或時間說明",
      "excludedKeywords": ["全聯", "7-11", "全家", "水電費", "繳稅"]
    }}
  ]
}}
注意事項：
1. 若有註明登錄或限量，務必設定 needReg: true。
2. 數值請為數字或 null。只輸出合法純 JSON，不包含 markdown 標記。

網頁內容如下：
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
    
    # 1. 預設先載入基準資料，確保核心卡片與登錄資料完整存在
    cards_dict = {f"{c['bank']}_{normalize_card_name(c['cardName'])}": c for c in DEFAULT_CARDS}
    rules_dict = {r["id"]: r for r in DEFAULT_RULES}

    # 2. 讀取現有 data.json 既有資料（累加而不洗白）
    if os.path.exists(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                for c in old_data.get("cards", []):
                    key = f"{c.get('bank')}_{normalize_card_name(c.get('cardName'))}"
                    if key and key not in cards_dict:
                        cards_dict[key] = c
                for r in old_data.get("rules", []):
                    if r.get("id") and r["id"] not in rules_dict:
                        rules_dict[r["id"]] = r
        except Exception:
            pass

    # 3. 爬取線上最新活動並合併
    for portal in BANK_PORTALS:
        print(f"開始抓取: {portal['bank']}...")
        text = fetch_content(portal["url"])
        if not text:
            print(f"  - 跳過 {portal['bank']}（未取得文字內容）")
            continue
        res = parse_bank_data(portal["bank"], text)
        if not res:
            print(f"  - 跳過 {portal['bank']}（AI 解析無有效輸出）")
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
                print(f"  🔥 捕獲登錄活動: {title}")
            else:
                print(f"  + 常規回饋規則: {title}")

    data = {
        "version": datetime.utcnow().strftime("%Y.%m.%d-v%H%M%S"),
        "lastUpdated": datetime.utcnow().isoformat() + "Z",
        "cards": list(cards_dict.values()),
        "rules": list(rules_dict.values()),
        "commonExclusions": [
            {"keywords": ["全聯", "pxmart"], "message": "全聯福利中心多數信用卡列為非一般消費，不給予一般回饋。"},
            {"keywords": ["7-11", "全家", "超商", "便利商店"], "message": "超商實體刷卡多數排除一般回饋，建議改用指定行動支付綁定。"}
        ]
    }

    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    total_reg = sum(1 for r in data["rules"] if r.get("needReg"))
    print(f"\n[完成] data.json 產出成功！總卡片數: {len(data['cards'])}, 總規則數: {len(data['rules'])}, 其中需要登錄活動數: {total_reg}")

if __name__ == "__main__":
    main()
