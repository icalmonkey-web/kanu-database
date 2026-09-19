import os
import json
import re
from datetime import datetime
from google import genai
from google.genai import types

# 1. 初始化 AI 客戶端
api_key = os.environ.get("GEMINI_API_KEY", "")
if not api_key:
    raise ValueError("GEMINI_API_KEY 環境變數未設定！")

client = genai.Client(api_key=api_key)

# 2. 只需要各大銀行的官網信用卡總覽連結
FULL_MARKET_PORTALS = [
    {"bank": "國泰世華", "url": "https://www.cathaybk.com.tw/cathaybk/personal/product/credit-card/cards/"},
    {"bank": "玉山銀行", "url": "https://www.esunbank.com/zh-tw/personal/credit-card/intro/bank-card"},
    {"bank": "台新銀行", "url": "https://www.taishinbank.com.tw/TSB/personal/credit/intro/overview/cg021/card001/"},
    {"bank": "台北富邦", "url": "https://www.fubon.com/banking/personal/credit_card/all_card/all_card.htm"},
    {"bank": "永豐銀行", "url": "https://bank.sinopac.com/sinopacBT/personal/credit-card/introduction/list.html"},
    {"bank": "中國信託", "url": "https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/index.html"},
    {"bank": "聯邦銀行", "url": "https://activity.ubot.com.tw/2023JiHeCard/index.htm"},
    {"bank": "星展銀行", "url": "https://www.dbs.com.tw/personal-zh/cards/ecocard/default.page"},
    {"bank": "滙豐銀行", "url": "https://www.hsbc.com.tw/credit-cards/products/live-plus/"}
]

def normalize_card_name(name):
    if not name:
        return ""
    n = re.sub(r"\s+", "", name).upper()
    n = re.sub(r"(信用卡|御璽卡|鈦金卡|晶緻卡|無限卡|世界卡|白金卡|商務卡|聯名卡|卡)$", "", n)
    return n

def ask_gemini_to_read_url(bank_name, target_url):
    """直接把 URL 丟給 Gemini，搭配 Google Search 工具聯網即時研讀"""
    prompt = f"""
你現在是專業金融情報專家。請你直接透過聯網功能，深入瀏覽與研讀以下這個【{bank_name}】的官方信用卡網址：
網址：{target_url}

請你閱讀該頁面所有內容，自主萃取出該頁面介紹的所有「信用卡名稱」、「消費回饋方案」與「需要登錄的加碼活動」。

請嚴格輸出合法純 JSON 格式：
{{
  "cards": [
    {{
      "id": "英數唯一碼(例: {bank_name}_1)",
      "bank": "{bank_name}",
      "cardName": "信用卡全名",
      "themeBg": "linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)",
      "textColor": "#ffffff",
      "descTag": "核心特色簡述(10字內)"
    }}
  ],
  "rules": [
    {{
      "id": "規則唯一碼",
      "cardId": "對應卡片的id",
      "title": "回饋活動名稱",
      "scope": "ALL 或 SPECIFIC",
      "matchedMerchants": ["特約店家名單"],
      "searchKeywords": "AI自主聯想之所有搜尋情境詞與代表品牌(以逗號隔開)",
      "baseRate": 1.0,
      "promoRate": 2.0,
      "capAmount": 500,
      "needReg": false,
      "regDeadline": "登錄時間或說明",
      "quotaInfo": "名額限制",
      "excludedKeywords": ["明確排除不回饋項目"]
    }}
  ]
}}

原則：
1. 請務必聯網檢索該網址與該銀行的真實最新資訊，不可自行捏造。
2. 只要該頁面有提及的卡片與回饋，請完整提取。
3. 只回傳純 JSON，絕不包含 ```json 或任何額外開場白。
"""
    try:
        # 使用支援聯網工具的 gemini-2.5-flash 模型
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())], # 啟用 Google 聯網能力
                temperature=0.2
            )
        )
        if not response or not response.text:
            return None

        # 清洗 JSON
        raw = response.text.strip()
        clean = re.sub(r"^```(json)?", "", raw, flags=re.IGNORECASE)
        clean = re.sub(r"```$", "", clean.strip())
        
        start_idx = clean.find("{")
        end_idx = clean.rfind("}")
        if start_idx != -1 and end_idx != -1:
            clean = clean[start_idx:end_idx+1]

        return json.loads(clean.strip())
    except Exception as e:
        print(f"    ❌ AI 聯網讀取或解析失敗 ({bank_name}): {e}")
        return None

def main():
    db_path = "data.json"
    data = {
        "version": "2026.09.20-v0",
        "cards": [],
        "rules": [],
        "commonExclusions": [
            {"keywords": ["全聯", "pxmart"], "message": "全聯福利中心多數信用卡列為「非一般消費」無回饋。"},
            {"keywords": ["7-11", "全家", "超商", "便利商店"], "message": "超商實體刷卡多列為排除名單，建議搭配指定行動支付。"},
            {"keywords": ["水費", "電費", "瓦斯", "公用事業", "學費", "稅款"], "message": "政府規費、公用事業水電瓦斯多數信用卡皆排除回饋。"}
        ]
    }

    cards_map = {}
    rules_map = {}
    if os.path.exists(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                for c in old_data.get("cards", []):
                    key = f"{c.get('bank')}_{normalize_card_name(c.get('cardName'))}"
                    cards_map[key] = c
                for r in old_data.get("rules", []):
                    rules_map[r.get("id")] = r
        except Exception:
            pass

    for portal in FULL_MARKET_PORTALS:
        bank = portal["bank"]
        url = portal["url"]
        print(f"\n==============================")
        print(f"直接交由 Gemini 聯網研讀: [{bank}] {url}...")

        result = ask_gemini_to_read_url(bank, url)
        if not result or not result.get("cards"):
            print(f"  - 跳過 {bank}（未能取得有效卡片內容）")
            continue

        id_map = {}
        for c in result.get("cards", []):
            raw_name = c.get("cardName", "").strip()
            if not raw_name:
                continue
            norm_key = f"{bank}_{normalize_card_name(raw_name)}"
            if norm_key not in cards_map:
                std_id = f"card_{bank}_{len(cards_map) + 1}"
                c["id"] = std_id
                cards_map[norm_key] = c
                print(f"  + 新卡入庫: [{bank}] {raw_name}")
            id_map[c.get("id")] = cards_map[norm_key]["id"]

        for r in result.get("rules", []):
            title = r.get("title", "").strip()
            if not title:
                continue
            if r.get("cardId") in id_map:
                r["cardId"] = id_map[r["cardId"]]
            rule_key = f"{r.get('cardId')}_{title}"
            rules_map[rule_key] = r
            if r.get("needReg"):
                print(f"  🔥 登錄活動: {title}")
            else:
                print(f"  + 權益條款: {title}")

    data["cards"] = list(cards_map.values())
    data["rules"] = list(rules_map.values())
    data["version"] = datetime.utcnow().strftime("%Y.%m.%d-v%H%M%S")
    data["lastUpdated"] = datetime.utcnow().isoformat() + "Z"

    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    total_reg = sum(1 for r in data["rules"] if r.get("needReg"))
    print(f"\n==============================")
    print(f"[完成] 全市場資料庫更新完畢！")
    print(f"總卡片數: {len(data['cards'])}, 總規則數: {len(data['rules'])}, 需登錄活動數: {total_reg}")

if __name__ == "__main__":
    main()
