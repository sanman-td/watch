#!/usr/bin/env python3
"""ドーミーイン出雲 2027年11月 予約受付開始ウォッチャー (Playwright版)

  python dormy_watch.py --show   調整用: 画面の文字と判定結果を表示
  python dormy_watch.py          監視: 新たに予約が表示されたら通知
"""
import os, sys, json, re, pathlib
from urllib.parse import urlencode
import requests
from playwright.sync_api import sync_playwright

# ---- 設定 -------------------------------------------------
CHECKIN = "2026/12/01"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "change-me-to-a-secret-topic")
# 料金欄が「-」でなく数字などになったら受付開始とみなす
OPEN_PATTERN = re.compile(r"[^\s\-]\s*\(消費税込\)")
CLOSED_PATTERN = re.compile(r"受付期間外|ご予約いただけません")
STATE_FILE = pathlib.Path(__file__).with_name(".dormy_state.json")
# ------------------------------------------------------------

QUERY = [
    ("checkin", CHECKIN), ("number_of_nights", 1), ("search_by_tag", "plan"),
    ("keyword", "天然温泉 八雲の湯 ドーミーイン出雲"), ("number_of_rooms", 1),
    ("stock_check", "true"), ("tags", ""), ("brands", ""), ("order_by", ""),
    ("number_of_adults[]", 2), ("number_of_children_need_futons[]", 0),
    ("number_of_children_no_need_futons[]", 0),
]
URL = "https://dormy-hotels.com/reserve/search-plan?" + urlencode(QUERY)


def fetch_text():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(locale="ja-JP")
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(15000)  # 検索結果の描画待ち
        text = page.inner_text("body")
        browser.close()
    return " ".join(text.split())


def notify(msg):
    requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode("utf-8"),
                  headers={"Title": "Dormy Inn Izumo", "Priority": "high"}, timeout=15)


def main():
    text = fetch_text()
    if "--show" in sys.argv:
        i = text.find("プランを選択")
        print(text[i:i + 2500] if i >= 0 else text[:2500])
        print("\nチェックイン表示:", re.findall(r"20\d\d/\d\d/\d\d", text)[:3])
        print("料金「-」の件数:", len(re.findall(r"-\s*\(消費税込\)", text)),
              "/ 料金あり(数字等)の件数:", len(OPEN_PATTERN.findall(text)))
        print("OPEN一致:", bool(OPEN_PATTERN.search(text)),
              "/ CLOSED一致:", bool(CLOSED_PATTERN.search(text)))
        return

    is_open = bool(OPEN_PATTERN.search(text)) and not CLOSED_PATTERN.search(text)
    was_open = json.loads(STATE_FILE.read_text()).get("open") if STATE_FILE.exists() else False
    if is_open and not was_open:
        notify(f"{CHECKIN} 宿泊の予約が表示されました!\n{URL}")
        out = os.environ.get("GITHUB_OUTPUT")
        if out:
            with open(out, "a") as f:
                f.write("found=true\n")
    STATE_FILE.write_text(json.dumps({"open": is_open}))


if __name__ == "__main__":
    main()
