#!/usr/bin/env python3
"""
TicketPlus 釋票監控（只偵測 + 通知，不自動購票）

用途：定期查詢 Vaundy 2026/11/1 台北小巨蛋場次的官方票務 API，
一旦任何票區狀態不是 soldout（代表有票釋出），就發出 macOS 桌面通知
+ 聲音提示，並可選擇寄送 Email。偵測到之後不會自動選票或結帳，
仍需要你自己手動登入 TicketPlus 完成購買（實名制購票本來就需要
你本人的身分證資料，且大部分售票平台的服務條款與台灣法規都禁止
使用程式自動搶票/購票）。

用法：
    python3 monitor.py                  # 每 60 秒查一次，查到有票就持續提醒直到你按 Ctrl+C
    python3 monitor.py --interval 30    # 自訂查詢間隔（秒），建議不要低於 15 秒以免對伺服器造成負擔

Telegram 手機推播（選用，設定後電腦+手機會同時收到通知）：
    設定以下環境變數：
        export TP_TG_BOT_TOKEN="123456789:ABCdefGhIJKlmNoPQRstuVwxYZ"
        export TP_TG_CHAT_ID="123456789"
    取得方式見 README.md。

Email 通知（選用）：
    設定以下環境變數後才會寄信，否則只會有桌面通知：
        export TP_SMTP_USER="you@gmail.com"
        export TP_SMTP_APP_PASSWORD="xxxx xxxx xxxx xxxx"   # Gmail 應用程式密碼，不是登入密碼
        export TP_NOTIFY_EMAIL="amber.pinyisung@gmail.com"
    Gmail 應用程式密碼申請：https://myaccount.google.com/apppasswords
"""

import argparse
import json
import os
import smtplib
import subprocess
import sys
import time
import urllib.request
from email.mime.text import MIMEText

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(SCRIPT_DIR, ".env")


def load_env_file(path):
    """Load KEY=VALUE lines from a local .env file into os.environ.

    Needed because launchd (unlike an interactive shell) does not source
    ~/.zshrc, so `export` vars set in a terminal aren't visible when this
    script is run as a background LaunchAgent.
    """
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


load_env_file(ENV_FILE)

ORDER_URL = "https://ticketplus.com.tw/order/a56fce0af2da4d41e26b2dfa34b7babc/debf14611c86559f4c28d8005b063ccf"

TICKET_AREA_IDS = [
    "a000007975", "a000007976", "a000007977", "a000007978",
    "a000007979", "a000007980", "a000007981", "a000007982", "a000007983",
    "a000007984", "a000007985", "a000007986", "a000007987", "a000007988",
    "a000007989", "a000007990", "a000007991", "a000007992", "a000007993",
    "a000007994", "a000007995", "a000007996", "a000007997", "a000007998",
    "a000007999", "a000008000", "a000008001", "a000008002", "a000008003",
    "a000008028", "a000008029", "a000008030", "a000008031", "a000008032",
    "a000008033", "a000008034", "a000008035", "a000008004", "a000008005",
    "a000008006", "a000008007", "a000008008", "a000008009", "a000008010",
    "a000008011", "a000008012", "a000008013", "a000008014", "a000008015",
    "a000008016", "a000008017", "a000008018", "a000008019", "a000008020",
    "a000008021", "a000008022", "a000008023", "a000008024", "a000008025",
    "a000008026", "a000008027", "a000008036", "a000008037", "a000008038",
    "a000008039", "a000008040", "a000008041", "a000008042", "a000008043",
    "a000008044", "a000008045", "a000008046", "a000008047", "a000008048",
    "a000008049", "a000008050", "a000008051", "a000008052", "a000008053",
]

PRODUCT_IDS = [
    "p000014364", "p000014365", "p000014366", "p000014367", "p000014368",
    "p000014369", "p000014370", "p000014371", "p000014372", "p000014373",
    "p000014374", "p000014375", "p000014376", "p000014377", "p000014378",
    "p000014379", "p000014380", "p000014381", "p000014382", "p000014383",
    "p000014384", "p000014385", "p000014386", "p000014387", "p000014388",
    "p000014389", "p000014390", "p000014391", "p000014392", "p000014393",
    "p000014394", "p000014395", "p000014396", "p000014397", "p000014398",
    "p000014399", "p000014400", "p000014401", "p000014402", "p000014403",
    "p000014404", "p000014405", "p000014406", "p000014407", "p000014408",
    "p000014409", "p000014410", "p000014411", "p000014412", "p000014413",
    "p000014414", "p000014415", "p000014416", "p000014417", "p000014418",
    "p000014419", "p000014420", "p000014421", "p000014422", "p000014423",
    "p000014424", "p000014425", "p000014426", "p000014427", "p000014428",
    "p000014429", "p000014430", "p000014431", "p000014432", "p000014433",
    "p000014445", "p000014449", "p000014450", "p000014451", "p000014452",
    "p000014453", "p000014454", "p000014455", "p000014456",
]

API_URL = (
    "https://apis.ticketplus.com.tw/config/api/v1/get"
    "?ticketAreaId=" + "%2C".join(TICKET_AREA_IDS)
    + "&productId=" + "%2C".join(PRODUCT_IDS)
)


def fetch_ticket_areas():
    req = urllib.request.Request(API_URL, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["result"]["ticketArea"]


def mac_notify(title, message):
    if sys.platform != "darwin":
        return
    script = f'display notification "{message}" with title "{title}" sound name "Glass"'
    try:
        subprocess.run(["osascript", "-e", script], check=False)
    except FileNotFoundError:
        pass


def send_telegram(available_areas):
    bot_token = os.environ.get("TP_TG_BOT_TOKEN")
    chat_id = os.environ.get("TP_TG_CHAT_ID")
    if not (bot_token and chat_id):
        return

    lines = [f"{a['ticketAreaName']} NT${a['price']}" for a in available_areas]
    text = (
        "\U0001f39f️ Vaundy 11/1 台北小巨蛋場次有票釋出！\n\n"
        + "\n".join(lines)
        + f"\n\n請立即前往結帳（需自行手動完成購票）：\n{ORDER_URL}"
    )
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )
    urllib.request.urlopen(req, timeout=15)


def send_email(available_areas):
    smtp_user = os.environ.get("TP_SMTP_USER")
    smtp_pass = os.environ.get("TP_SMTP_APP_PASSWORD")
    to_addr = os.environ.get("TP_NOTIFY_EMAIL")
    if not (smtp_user and smtp_pass and to_addr):
        return

    lines = [f"{a['ticketAreaName']} NT${a['price']}" for a in available_areas]
    body = (
        "偵測到 Vaundy 11/1 台北小巨蛋場次有票釋出：\n\n"
        + "\n".join(lines)
        + f"\n\n請立即前往結帳（需自行登入並手動完成購票）：\n{ORDER_URL}\n"
    )
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = "\U0001f39f️ Vaundy 11/1 場次有票釋出！"
    msg["From"] = smtp_user
    msg["To"] = to_addr

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [to_addr], msg.as_string())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=int, default=60, help="查詢間隔秒數（預設 60，建議不低於 15）")
    parser.add_argument("--once", action="store_true", help="只查一次就結束（給 GitHub Actions/cron 用，不進入迴圈）")
    args = parser.parse_args()

    if args.interval < 15:
        print("為避免對票務伺服器造成負擔，間隔不可低於 15 秒", file=sys.stderr)
        sys.exit(1)

    if not args.once:
        print(f"開始監控（每 {args.interval} 秒查詢一次）... 按 Ctrl+C 停止")
    already_notified = False

    while True:
        try:
            areas = fetch_ticket_areas()
            available = [a for a in areas if a.get("status") != "soldout"]
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

            if available:
                print(f"[{timestamp}] 發現 {len(available)} 個票區有票！")
                for a in sorted(available, key=lambda x: x["price"]):
                    print(f"  - {a['ticketAreaName']}  NT${a['price']}  status={a['status']}")
                if not already_notified:
                    mac_notify("Vaundy 11/1 有票了！", f"{len(available)} 個票區可購買，請立即前往結帳")
                    try:
                        send_telegram(available)
                    except Exception as e:
                        print(f"Telegram 推播失敗：{e}", file=sys.stderr)
                    try:
                        send_email(available)
                    except Exception as e:
                        print(f"Email 通知失敗：{e}", file=sys.stderr)
                    already_notified = True
            else:
                print(f"[{timestamp}] 目前無票（{len(areas)} 個票區皆售完）")
                already_notified = False

        except Exception as e:
            print(f"查詢失敗：{e}", file=sys.stderr)

        if args.once:
            break

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
