# YouTube JuEunBeautify

在每個 YouTube 影片縮圖上疊加 李珠珢 (JuEun) 的圖片。

![Preview](preview.png)

基於 [MrBeastify-Youtube](https://github.com/MagicJinn/MrBeastify-Youtube) 改作。

[English README](README-en.md)

## 安裝

**Chrome：** 前往 `chrome://extensions` → 開啟開發人員模式 → 載入未封裝項目 → 選擇本專案資料夾

**Firefox：** 前往 `about:debugging` → 此 Firefox → 載入暫時性附加元件 → 選擇 `manifest.firefox.json`

## 準備圖片

1. 安裝依賴套件：

```bash
pip install -r requirements.txt
```

2. 選擇模式：

### 縮圖模式 — 抓取 YouTube 封面圖

```bash
python prepare_images.py <youtube_url> [<youtube_url> ...]
```

### 影片截圖模式 — 從影片中擷取畫面

```bash
python prepare_images.py --frames <youtube_url> [選項]
```

| 選項 | 預設值 | 說明 |
|------|--------|------|
| `--fps 2` | 1 | 每秒擷取幾張畫面 |
| `--start 1m30s` | — | 開始時間（支援 `1m30s`、`1:30`、`90s`、`90`） |
| `--end 2m` | — | 結束時間 |
| `--auto 6` | — | 自動挑選 N 張最佳畫面 |
| `--pick 5,12,30` | — | 手動指定要處理的畫面編號 |
| `--model birefnet-portrait` | birefnet-portrait | 去背模型 |

**範例：**
```bash
python prepare_images.py --frames https://www.youtube.com/watch?v=XXXX --start 10s --end 2m --auto 8
```

輸出：`images/1.png`、`images/2.png`、...（透明背景 PNG）  
索引：`images/count.json` 會自動更新。

## 圖片格式

- PNG 透明背景
- 命名：從 `1.png` 開始的連續整數
- 如果圖片包含文字，鏡像後會看起來怪，請將編號加入 `images/flip_blacklist.json`

`flip_blacklist.json` 範例：
```json
[2, 5]
```
