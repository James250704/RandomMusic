# YouTube Music 播放清單隨機打亂工具 (RandomMusic)

這是一個自動化的 Python 腳本，專門用來將指定的 YouTube Music 播放清單內的歌曲順序**隨機打亂**。

腳本結合了 `DrissionPage` 來自動啟動無頭瀏覽器，動態獲取播放清單中的完整歌曲（自動向下捲動載入）及背後的授權憑證（Cookies、Tokens），接著使用 `httpx` 異步且高效地發送 API 請求批量修改歌曲順序。

## ✨ 功能特色

- **全自動抓取**：自動向下捲動載入播放清單中的所有歌曲，無需手動介入。
- **免手動配憑證**：透過瀏覽器自動提取當下的授權環境（包含 `INNERTUBE_CONTEXT` 與自行計算 `SAPISIDHASH`）。
- **非同步高效請求**：使用 `httpx` 送出基於 HTTP/2 的異步 API 請求，將排序動作分批（Batch）發送，提高執行效率。
- **無頭模式 (Headless)**：在背景無痕運行，自動配置 User-Agent 及參數以避免被網站偵測阻擋。

## 🛠️ 環境需求

- **Python 3.12+**
- 推薦使用 [uv](https://github.com/astral-sh/uv) 或 `pip` 作為套件管理工具。
- 本機需安裝 Google Chrome 或任一 Chromium 核心的瀏覽器（用於 DrissionPage）。

### 依賴套件
- `DrissionPage`
- `httpx[http2]`

## 🚀 安裝與使用方式

1. **取得程式碼與安裝依賴**  
   在專案目錄下執行以下指令安裝依賴（以 `uv` 為例）：
   ```bash
   uv pip install -r requirements.txt
   # 或者是使用傳統 pip:
   # pip install -r requirements.txt
   ```

2. **登入 YouTube Music**  
   由於需要編輯播放清單的權限，腳本運行時會讀取瀏覽器的本機狀態。若您從未在該環境登入過 YouTube 帳號，請先正常開啟 Chrome 並登入您的 YouTube Music。

3. **執行主程式**
   ```bash
   uv run main.py
   # 或者是
   # python main.py
   ```

4. **輸入播放清單 ID**  
   程式啟動後會提示輸入播放清單 ID。您可以在 YouTube Music 播放清單的網址中找到它 `list=後面的字串`。
   ![範例](https://music.youtube.com/playlist?list=PLNRXiocLwPncRjAQpwSYt_iXr3Cd5Nl4K)  
   👉 `PLNRXiocLwPncRjAQpwSYt_iXr3Cd5Nl4K` 就是播放清單 ID。
   
   ```text
   請輸入播放清單 ID：在此處貼上您的播放清單 ID
   ```

5. **等待執行完畢**  
   終端機會顯示目前的進度，包含成功獲取的歌曲數量、分拆的封包數以及發送狀態。看到 `✅ 全體任務處理完畢。` 即可至 YouTube Music 確認打亂結果。

## ⚠️ 注意事項

- **權限需求**：只能對**自己擁有編輯權限**的播放清單進行操作（例如自己建立的清單）。
- **請求限制**：如果遇到 `409 衝突` 或 `讀取超時` 的情況，腳本內已實做了簡單的等待與重試邏輯，但請避免在短時間內極高頻繁使用，以免遭到 YouTube 的暫時性速率限制。
- 此工具僅為學術研究與自動化學習用途，請遵守相關平台的服務條款。
