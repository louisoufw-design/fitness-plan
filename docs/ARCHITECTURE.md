# 架構與資料結構

全部程式碼都在 `index.html` 的一個 `<script>` 裡，用 IIFE 包起來，沒有全域變數，也沒有外部 JS 依賴。

## 儲存

| 鍵 | 位置 | 內容 |
|---|---|---|
| `spike-log-v2` | localStorage（每次 `commit()` 都會寫） | `log`：使用者的完整紀錄，會同步 |
| `spike-ui-v2` | localStorage | `ui`：這台裝置的畫面狀態，不同步 |
| `data/users/<userId>/log` | 遠端（目前是 Claude 的 `db` 能力） | 和 `log` 同一份文件 |

鍵名裡的 `spike` 是早期版本留下來的名字。改名會讓舊使用者的紀錄讀不到，所以保留。

### 遠端 adapter 介面

```js
// REMOTE = { open, load, save, watch }
open()    // → Promise<boolean>      連線；這個環境用不了時回傳 false
load()    // → Promise<object|null>  已存的紀錄
save(doc) // → Promise               失敗時 reject { fatal: true } 停止同步，或 { retry: true } 再試一次
watch(cb) // → void                  其他裝置存檔時呼叫 cb(doc)
```

兩邊衝突時，`updated`（毫秒時間戳）比較新的那份勝出。要換成 Supabase、Firebase 或自己的 API，就寫一個同樣介面的 adapter，再把 `var REMOTE = claudeDb;` 指向它，其他程式碼不用改。

## `log` 的結構（DATA_VERSION 5）

```js
{
  v: 5,
  prog: 'novice' | 'fullbody' | 'upperlower' | 'ppl' | 'spike' | 'mine',  // 使用中的課表
  pm: { [programId]: '3' },          // 每套課表的每週目標次數
  pstart: 'YYYY-MM-DD' | null,       // 開始用這套課表的日期
  start: 'YYYY-MM-DD' | null,        // 扣球爆發 8 週週期的開始日
  myprog: null | {                   // 「量身排一套」產生的課表
    name, made, tags: [], desc,
    opts: { n, split, eq, goal, min },
    days: [{ name, abbr, focus, items: [{ ex, alts: [], sets, reps, rest, per }] }]  // 最多 6 天，每天最多 8 個動作
  },
  swaps: { [slotCode]: exerciseId }, // 使用者在某個位置換掉的動作
  workouts: [{
    id, d: 'YYYY-MM-DD', day: 'A', t0, t1, last,   // t0 開始、t1 結束（毫秒）
    ex: [{ slot: 'A1', id: 'goblet_squat', rpe, tgt: { sets, reps }, sets: [{ w /* kg */, r, done }] }],
    add: [{ id, sets, reps, per, rest }]            // 當天臨時加的動作（位置 AE1…AE6）
  }],
  settings: { name, unit: 'kg'|'lb', theme, autoRest, restSound, vibrate, awake, avoid: [exerciseId] },
  custom: { d, items: [] },          // 「自己排」當天的菜單（訓練日 X）
  diet: { sex, age, h, goal, ... },  body: [{ d, w }],  bw,
  tests, lines, diag,                // 舊版排球功能的資料：保留，但介面已不顯示
  updated: 1700000000000
}
```

改資料結構時：把 `DATA_VERSION` 加一，並在 `normalize()` 裡處理舊資料。`normalize()` 是資料進來的唯一入口，會修正或丟掉格式不對的內容。

## 課表與輪流

- 訓練日 id 是一個字母，動作位置（slot）是「訓練日 id + 序號」。訓練日 id 對照：
  - 扣球爆發：A B C D
  - 新手器械入門：N M
  - 5×5：F G
  - PHUL：U L V W
  - PPL：Q P R J H
  - 自己排：X
  - 我的課表：K O Y Z I T
- 每套課表有 `order`，也就是輪流的順序。`nextIdx()` 依日期順序走過這套課表的訓練紀錄：每次訓練把指標移到那一天的下一天。所以漏掉一天不會打亂順序，臨時跳著練也能接得上。
- 每週目標次數 `modeOf(p)` 只用來顯示「這週 x / y 次」，不綁星期幾。
- 「我的課表」的 6 天 × 8 個位置一開始就存在，`applyMine(log.myprog)` 會把它們填滿；紀錄、換動作和建議重量都和其他課表共用同一套程式碼。

## 不做的動作

`settings.avoid` 是動作 id 的陣列。用在這幾個地方：

- `libFor(slot)`：遇到不做的動作，改用替代清單裡第一個可以做的。
- 「自己排」和「量身排一套」挑動作時會略過不做的動作。
- 「加入動作」清單會把不做的動作排到最後。
