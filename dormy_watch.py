#!/usr/bin/env python3
"""ドーミーイン出雲 2027年11月 予約受付開始ウォッチャー

使い方:
  pip install requests beautifulsoup4
  1) 調整:   python dormy_watch.py --show    (今の状態のページ文字列を確認)
  2) 常時監視: python dormy_watch.py         (cronなどで30分おきに実行)

通知: スマホアプリ「ntfy」をインストールし、推測されにくいトピック名を
      NTFY_TOPIC に設定すると、プッシュ通知が届きます(無料)。
"""
import os, sys, json, re, pathlib
import requests
from bs4 import BeautifulSoup

# ---- 設定 -------------------------------------------------
CHECKIN = "2027/11/01"   # 11月分が開くと、まず11/1が予約可能になるはず
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "change-me-to-a-secret-topic")
# 「予約できる」ときだけ出る文字(例: 料金表示)。--show で確認して調整
OPEN_PATTERN = re.compile(r"[\d,]+円")
# 「まだ受付前」のときに出る文字。--show で確認して調整
CLOSED_PATTERN = re.compile(r"該当するプランがありません|受付期間外|ご予約いただけません|空室がありません")
STATE_FILE = pathlib.Path(__file__).with_name(".dormy_state.json")
# ------------------------------------------------------------

URL = "https://dormy-hotels.com/reserve/search-plan"
PARAMS = {
    "checkin": CHECKIN, "number_of_nights": 1, "search_by_tag": "plan",
    "keyword": "天然温泉 八雲の湯 ドーミーイン出雲", "number_of_rooms": 1,
    "stock_check": "true", "number_of_adults[]": 2,
    "number_of_children_need_futons[]": 0,
    "number_of_children_no_need_futons[]": 0,
}


def fetch_text():
    r = requests.get(URL, params=PARAMS, timeout=30,
                     headers={"User-Agent": "Mozilla/5.0 (personal availability check)"})
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)


def notify(msg):
    requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode("utf-8"),
                  headers={"Title": "Dormy Inn Izumo", "Priority": "high"}, timeout=15)


def main():
    text = fetch_text()
    if "--show" in sys.argv:
        print(text[:3000])
        print("\nOPEN一致:", bool(OPEN_PATTERN.search(text)),
              "/ CLOSED一致:", bool(CLOSED_PATTERN.search(text)))
        if len(text) < 500:
            print("※本文が少ない場合、JavaScriptで描画されている可能性があります。"
                  "その場合は Playwright 版に切り替えてください。")
        return

    is_open = bool(OPEN_PATTERN.search(text)) and not CLOSED_PATTERN.search(text)
    was_open = json.loads(STATE_FILE.read_text()).get("open") if STATE_FILE.exists() else False
    if is_open and not was_open:
        notify(f"{CHECKIN} 宿泊の予約が表示されました!\n{requests.Request('GET', URL, params=PARAMS).prepare().url}")
        # GitHub Actions上なら「見つかった」を伝え、ワークフロー側で監視を停止させる
        out = os.environ.get("GITHUB_OUTPUT")
        if out:
            with open(out, "a") as f:
                f.write("found=true\n")
    STATE_FILE.write_text(json.dumps({"open": is_open}))


if __name__ == "__main__":
    main()
