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
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-1.5-flash"
]

# 2. 全台灣主流發卡銀行「全卡片總覽入口」
FULL_MARKET_PORTALS = [
    # 國泰世華信用卡全產品總覽
    {
        "bank": "國泰世華",
        "url": "https://www.cathaybk.com.tw/cathaybk/personal/product/credit-card/cards/"
    },
    # 玉山銀行全卡片總覽
    {
        "bank": "玉山銀行",
        "url": "https://www.esunbank.com/zh-tw/personal/credit-card/intro/bank-card"
    },
    # 台新銀行信用卡全產品總覽
    {
        "bank": "台新銀行",
        "url": "https://www.taishinbank.com.tw/TSB/personal/credit/intro/overview/"
    },
    # 台北富邦信用卡全列表
    {
        "bank": "台北富邦",
        "url": "https://www.fubon.com/banking/personal/credit_card/all_card/all_card.htm"
    },
    # 中國信託信用卡總覽
    {
        "bank": "中國信託",
        "url": "https://www.ctbcbank.com/content/dam/minisite/long/creditcard/index.html"
    },
    # 聯邦銀行信用卡總覽
    {
        "bank": "聯邦銀行",
        "url": "https://card.ubot.com.tw/eCard/Card/List.aspx"
    },
    # 永豐銀行信用卡總覽
    {
        "bank": "永豐銀行",
        "url": "https://bank.sinopac.com/sinopacBT/personal/credit-card/introduction/list.html"
    },
    # 星展銀行信用卡總覽
    {
        "bank": "星展銀行",
        "url": "https://www.dbs.com.tw/personal-zh/cards/default.page"
    },
    # 滙豐銀行信用卡總覽
    {
        "bank": "滙豐銀行",
        "url": "https://www.hsbc.com.tw/credit-cards/products/"
    },
    # 兆豐銀行信用卡總覽
    {
        "bank": "兆豐銀行",
        "url": "https://www.megabank.com.tw/personal/credit-card/card"
    }
]

def normalize_card_name(name):
    """卡片名稱正規化，清除空格與修飾詞以避免重複"""
    if not name:
        return ""
    n = re.sub(r"\s+", "", name).upper()
    n = re.sub(r"(信用卡|御璽卡|鈦金卡|晶緻卡|無限卡|世界卡|白金卡|卡)$", "", n)
    return n

def fetch_markdown_or_html(target_url):
    """優先透過 Jina Reader 獲取 Markdown，備援直連抓取"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,text/plain"
    }
    # 嘗試 Jina Reader
    try:
        jina_url = f"https://r.jina.ai/{target_url}"
        res = requests.get(jina_url, headers=headers, timeout=25)
        if res.status_code == 200 and len(res.text.strip()) > 300:
            return res.text
    except Exception:
        pass

    # 備援直連
    try:
        res = requests.get(target_url, headers=headers, timeout=20)
        if res.status_code == 200:
            clean_html = re.sub(r"<(script|style).*?</\1>", "", res.text, flags=re.DOTALL | re.IGNORECASE)
            return clean_html[:15000]
    except Exception:
        pass
    return ""

def call_gemini(prompt):
    """支援最新模型順序嘗試"""
    for model_name in CANDIDATE_MODELS:
        try:
            res = client.models.generate_content(model=model_name, contents=prompt)
            if res and res.text:
                return res.text
        except Exception:
            continue
    return None

def parse_full_bank_cards(bank_name, raw_content):
    """指示 AI 提取整家銀行的所有信用卡及權益規則"""
    prompt = f"""
你現在是專業金融與消費語意理解專家。請研讀【{bank_name}】信用卡權益條款，提取規則時請進行「領域與實體結構化」：

嚴格輸出純 JSON 格式：
{{
  "cards": [ ... ],
  "rules": [
    {{
      "id": "規則唯一識別碼",
      "cardId": "對應卡片id",
      "title": "回饋活動名稱",
      "domain": "主要領域(如: 餐飲, 國外/旅遊, 網購/電商, 行動支付, 交通, 一般消費)",
      "scope": "ALL(該領域全通用) 或 SPECIFIC(僅限官方特約名單)",
      "matchedMerchants": ["條款原文中明確提及之品牌或特定店家名單"],
      "searchKeywords": "AI自主聯想之5至8個核心情境搜尋詞與中英文頂級代表品牌(以逗號分隔)",
      "baseRate": 1.0,
      "promoRate": 2.0,
      "capAmount": 500,
      "needReg": false,
      "regDeadline": "登錄截止或時限說明",
      "quotaInfo": "名額限制",
      "excludedKeywords": ["條款明確排除之項目(如超商、全聯、水電公用事業、繳稅)"]
    }}
  ]
}}

原則：
1. 若 scope 為 ALL，searchKeywords 請聚焦該領域的通用代名詞與最常見頂級品牌（控制在 10 個詞以內），不必列出所有小店。
2. 若 scope 為 SPECIFIC，matchedMerchants 必須忠實列出條款所有特約品牌。
3. 輸出純 JSON，絕不夾帶任何額外符號或說明。
"""
    raw_response = call_gemini(prompt)
    if not raw_response:
        return None

    try:
        clean = re.sub(r"^```(json)?", "", raw_response.strip(), flags=re.IGNORECASE)
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
            {"keywords": ["全聯", "pxmart"], "message": "全聯福利中心多數銀行排除一般消費回饋。"},
            {"keywords": ["7-11", "全家", "萊爾富", "OK", "超商"], "message": "超商實體刷卡多數排除一般回饋，需搭配指定行動支付或特定卡片。"},
            {"keywords": ["繳稅", "水電", "瓦斯", "學費", "停車費"], "message": "公用事業規費與稅款多數全額排除回饋。"}
        ]
    }

    # 讀取現有資料庫進行累積式儲存
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

    # 逐一爬取全市場各家銀行的卡片總覽目錄
    for portal in FULL_MARKET_PORTALS:
        bank = portal["bank"]
        print(f"\n==============================")
        print(f"開始全量探索: {bank} 信用卡目錄...")
        content = fetch_markdown_or_html(portal["url"])
        if not content:
            print(f"  - 跳過 {bank}（無法取得網頁文字內容）")
            continue

        result = parse_full_bank_cards(bank, content)
        if not result:
            print(f"  - 跳過 {bank}（AI 解析無有效輸出）")
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
                print(f"  + 新卡片入庫: [{bank}] {raw_name}")
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
    print(f"\n[完成] 全市場資料庫更新完畢！")
    print(f"總卡片數: {len(data['cards'])}, 總規則數: {len(data['rules'])}, 需登錄活動數: {total_reg}")

if __name__ == "__main__":
    main()
