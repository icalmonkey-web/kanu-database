import os
import json
import requests
import google.generativeai as genai
from datetime import datetime

# 設定 Gemini API Key (由 GitHub Secrets 免費提供)
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

# 要監控的各銀行活動專區入口網址
BANK_PORTALS = [
    {"bank": "國泰世華", "url": "https://www.cathaybk.com.tw/cathaybk/personal/event/overview/"},
    {"bank": "玉山銀行", "url": "https://www.esunbank.com/zh-tw/personal/credit-card/discount/shops"},
]

def fetch_markdown_via_jina(target_url):
    # 使用 Jina Reader 免費將任何網頁轉成乾淨文字
    jina_url = f"https://r.jina.ai/{target_url}"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(jina_url, headers=headers, timeout=20)
    return res.text if res.status_code == 200 else ""

def parse_with_ai(bank_name, raw_content):
    prompt = f"""
    你現在是專業信用卡資料庫工程師。請分析以下【{bank_name}】的活動網頁文字內容。
    請提取有效信用卡活動，並依照下列 JSON 格式輸出：
    {{
      "cards": [
        {{ "id": "唯一英文數字", "bank": "{bank_name}", "cardName": "卡名", "descTag": "特色標籤" }}
      ],
      "rules": [
        {{
          "id": "唯一編號",
          "title": "活動名稱",
          "category": "適用通路關鍵字(請主動擴充同義詞，用逗號隔開)",
          "baseRate": 數字,
          "promoRate": 數字,
          "capAmount": 上限數字或 null,
          "needReg": true或false,
          "regDeadline": "截止時間或永久",
          "excludedKeywords": ["條款中載明排除的所有不回饋通路"]
        }}
      ]
    }}
    只需輸出純 JSON 字串，不要包含任何額外說明。
    網頁內容如下：
    {raw_content[:6000]}
    """
    response = model.generate_content(prompt)
    clean_json = response.text.replace("
```json", "").replace("```", "").strip()
    return json.loads(clean_json)

# 主流程：讀取舊資料 -> 抓取新資料 -> 比對合併 -> 寫回
# 若有更新，將 version 改為今日時間戳，如 "2026.09.20-v2"
