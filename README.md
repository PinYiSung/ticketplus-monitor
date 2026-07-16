# TicketPlus 釋票監控

只做「偵測 + 通知」，不會自動選票、填資料或結帳。偵測到有票時同時發出：
- 電腦桌面通知（macOS 內建，免設定）
- 手機 Telegram 推播（需要下面的設定）
- Email（選用）

## 1. 建立 Telegram Bot 取得 Token

1. 手機打開 Telegram，搜尋 **BotFather**（官方帳號，藍勾勾）並開始對話。
2. 傳送 `/newbot`，依照指示輸入 bot 名稱（例如 `我的搶票通知機器人`）與 username（必須以 `bot` 結尾，例如 `pinyi_ticket_alert_bot`）。
3. BotFather 會回傳一組 token，長得像：
   `123456789:ABCdefGhIJKlmNoPQRstuVwxYZ0123456789`
   複製起來備用。

## 2. 取得 Chat ID

1. 用手機 Telegram 搜尋你剛建立的 bot（用你設定的 username），點進去傳送任意一句話（例如 `hi`）。
   （這一步是必要的——bot 沒被使用者先私訊過，無法主動傳訊息給你。）
2. 在電腦瀏覽器打開（把 `<TOKEN>` 換成你的 token）：
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. 會看到一段 JSON，找到 `"chat":{"id":123456789,...}`，那個數字就是你的 Chat ID。

## 3. 設定環境變數並執行

```bash
export TP_TG_BOT_TOKEN="123456789:ABCdefGhIJKlmNoPQRstuVwxYZ0123456789"
export TP_TG_CHAT_ID="123456789"

cd ~/ticketplus_monitor
python3 monitor.py
```

有票時，電腦會跳桌面通知＋響一聲，手機 Telegram 也會同時收到訊息。

## 常駐執行（開電腦就自動跑，不用手動開終端機）

若想要背景長期執行，可以幫你設定 macOS launchd（開機/登入自動啟動、掛掉自動重啟），
需要的話跟我說一聲，我再幫你寫 plist 設定檔。

## 選用：Email 通知

```bash
export TP_SMTP_USER="you@gmail.com"
export TP_SMTP_APP_PASSWORD="xxxx xxxx xxxx xxxx"   # Gmail 應用程式密碼，不是登入密碼
export TP_NOTIFY_EMAIL="amber.pinyisung@gmail.com"
```
申請應用程式密碼：https://myaccount.google.com/apppasswords
