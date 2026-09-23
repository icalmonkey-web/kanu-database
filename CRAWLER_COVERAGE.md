# 掃描範圍與驗收

目標是每家銀行公開信用卡權益與登錄活動至少 95% 正確收錄。
目前尚無逐銀行人工核對基準，coveragePercent 固定為 null，不能宣稱達標。
入口清單仍有待逐家驗證；目前設定銀行數不是台灣所有發卡銀行的證明。

## 本版

- 每次從入口重新探索同網域相關連結，廣度優先，預設每銀行 150 頁、5 層。
- 分析入口本身及詳情；保留查詢參數、去除追蹤參數及片段，避免迴圈。
- 讀取同允許網域 iframe、data-href/data-url、捲動及明確的載入更多/下一頁按鈕。
- 不點擊登錄、申請、登入按鈕，不提交表單。外網域必須人工確認加入 allowed_hosts。
- 每頁長文字分段處理，所有分段成功才快取；AI 失敗下次重試。
- 舊資料不因本次抓取失敗而刪除，舊 fetchedAt 不假裝更新。
- crawl_report.json 每完成一家寫入；Actions 無論成功失敗都上傳已有報告。

## 報告不是涵蓋率

pages 包含 URL、來源父頁、深度、處理狀態、缺口。
unvisited 記錄頁數/深度限制留下的工作；externalCandidates 是待審核網域。
needs_review 表示有未完成或需檢查項目。
discovery_finished_unverified 只表示這次探索佇列結束，不代表所有活動已收錄。

## 尚未解決的驗收項目

- 各銀行入口正確性與完整發卡銀行名單。
- PDF、特殊 API、非標準互動式分頁及登入限定內容。
- 活動獨立基準清單、逐欄正確率與真正 95% 涵蓋率計算。
- 舊資料重複卡片及失聯 cardId 的清理；新資料無法對卡時標記 needs_review。
- 各銀行實站回歸測試；離線測試不證明官方網站可抓取。

執行離線測試：`python -m unittest discover -s .github/scripts -p 'test_*.py'`
可調環境變數：MAX_PAGES_PER_BANK、MAX_CRAWL_DEPTH、GEMINI_MODELS。
