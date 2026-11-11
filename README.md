# 健身課表

一個打開就能用的重訓 App：選課表或量身排一套、每組記重量和次數、休息計時、自動建議下次重量、練完伸展，加上飲食的熱量和蛋白質計算。整個 App 是**單一 HTML 檔**（`index.html`），沒有建置步驟、沒有後端。

介面是繁體中文（台灣），手機優先，支援淺色和深色模式。

## 功能

| 分頁 | 內容 |
|---|---|
| 重訓 › 訓練 | 當天菜單、每組記錄（公斤或磅）、休息計時、熱身組、下次重量建議、多做一組、臨時加動作、訓練模式、練完結算表 |
| 重訓 › 課表 | 5 套有來源的課表（新手器械入門、5×5、PHUL、推拉腿 PPL、扣球爆發）＋「量身排一套」產生器；**照順序輪流，不綁星期幾**，每週只設目標次數 |
| 重訓 › 自己排 | 輸入時間和部位，排出剛好用完時間的菜單 |
| 重訓 › 動作庫 | 約 65 個動作（含台灣連鎖健身房常見器械），每個有示意圖、重點、常見錯誤、示範影片和個人紀錄；可設成「我不做這個動作」 |
| 重訓 › 紀錄 | 每週總量、各部位組數、個人最佳（估計 1RM）、單一動作進步圖 |
| 重訓 › 伸展 | 依當天練的部位排好伸展，可跟著計時 |
| 飲食 | TDEE、蛋白質目標、體重紀錄、餐盤和菜單、食物表、素食專區 |
| 設定 | 暱稱、公斤／磅、主題、計時提示、不做的動作清單、匯入／匯出、清除紀錄 |

## 執行方式

### 只是要用
直接用瀏覽器打開 `index.html` 就可以。紀錄存在該瀏覽器的 `localStorage`。

或用任何靜態伺服器，例如：

```bash
python3 -m http.server 8000
# 打開 http://localhost:8000
```

也可以直接放上 GitHub Pages、Netlify、Vercel 等靜態網站服務。

### 在 Claude 裡使用（帳號同步）
這個檔案原本是 Claude 的 Artifact。在 Claude 裡打開時，App 會透過 `window.claude` 執行環境使用三個能力：

- `db`：把紀錄同步到使用者帳號（換裝置也看得到）
- `user`：取得使用者 id，決定資料路徑 `data/users/<id>/log`
- `downloads`：匯出 CSV 和 JSON 備份

在 Claude 以外打開時這些能力不存在，App 會自動退回只存本機，**匯出按鈕會隱藏**（匯入 JSON 和其他功能都正常）。

## 需要的套件與版本

| 用途 | 需要 |
|---|---|
| 執行 App | 任何近期的瀏覽器（Chrome、Safari、Firefox、Edge）。不需要 Node 或任何套件 |
| 字型（選用） | 從 Google Fonts 載入 Anton 和 Noto Sans TC；離線時會改用系統字型 |
| 執行測試 | Python 3.10 以上（開發時用 3.13）、Playwright 1.56.0、Chromium |

安裝測試環境：

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
```

執行測試：

```bash
cd tests
python test_smoke.py       # 13 個頁面 × 手機／桌機 × 淺色／深色：沒有錯誤、沒有橫向捲動、id 不重複、控制項都有名稱
python test_programs.py    # 輪流順序、換課表、量身排一套、不做的動作
```

測試會用 `tests/fakeclaude.js` 模擬 Claude 執行環境，並擋掉所有外部網路請求，所以可以離線跑。截圖會存到 `tests/shots/`（已列入 `.gitignore`）。想看到瀏覽器畫面，設 `HEADLESS=0`。

## 環境變數

**目前的版本不需要任何環境變數，也沒有任何金鑰。** App 是純前端，同步完全交給 Claude 執行環境處理。

`.env.example` 列的是：

- `HEADLESS`：測試用，`0` 會顯示瀏覽器視窗。
- 預留給之後接自己的資料庫（見下方「待辦」）的變數名稱，目前程式碼**不會讀取**。

真的接上資料庫時：

1. 複製 `.env.example` 成 `.env`，填入真的值。
2. `.env` 已在 `.gitignore` 裡，**不要提交到 GitHub**。
3. 前端拿得到的值都會被使用者看到，只能放公開用的 key，例如 Firebase Web API Key 或 Supabase anon key，並搭配資料庫的權限規則。服務端金鑰只能放在後端。

## 程式架構

所有程式碼都在 `index.html` 的一個 IIFE 裡，分成幾層（檔案開頭的註解有完整說明）：

- **內容資料**：`LIB`（動作）、`FIGS`（示意圖）、`VIDS`（影片連結）、`SLOTS` + `DAYS` + `PROGRAMS`（課表）、`STRETCHES`、食物表。新增動作就是加一筆 `LIB`（加上 `FIGS`、`VIDS`）。id 是紀錄指向的對象，不要重複使用。
- **紀錄 `log`**：使用者擁有的一切，包括訓練、體重、飲食資料、設定、使用中的課表、量身排的課表 `myprog`。所有資料進來都經過 `normalize()`（本機、遠端、匯入都一樣），版本號是 `DATA_VERSION`（目前 5）。重量一律存公斤。
- **裝置狀態 `ui`**：目前分頁、選的訓練日等，只存在本機。
- **設定**：`SETTINGS` schema，搭配 `setting(k)` 和 `setSetting(k, v)`。
- **儲存**：`commit()` 先寫本機，再交給 `REMOTE` adapter（介面是 `open / load / save / watch`）。要換成自己的資料庫，只要換掉這個 adapter。

詳細的資料結構見 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)，版本紀錄見 [`docs/CHANGELOG.md`](docs/CHANGELOG.md)。

## 課表和影片來源

- 新手器械入門：ACSM 2009 阻力訓練立場聲明（https://pubmed.ncbi.nlm.nih.gov/19204579/）
- 5×5 全身力量：StrongLifts 5×5（https://stronglifts.com/stronglifts-5x5/workout-program/）
- PHUL：Muscle & Strength（https://www.muscleandstrength.com/workouts/phul-workout）
- 推拉腿 PPL：Reddit r/Fitness，u/Metallicadpa（https://www.reddit.com/r/Fitness/comments/37ylk5/）
- 扣球爆發：依 App「須知」頁列出的排球與訓練研究設計
- 示範影片是 YouTube 上其他創作者的作品，App 只放連結，在新分頁打開。

## 免責聲明

本 App 提供一般的訓練和飲食資訊，不能取代醫師、物理治療師或教練的建議。

## 授權

尚未選擇授權條款。公開前請自行加入 `LICENSE`，例如 MIT。
