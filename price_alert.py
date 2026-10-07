import json, os, urllib.request, urllib.parse

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT = os.environ.get("TELEGRAM_CHAT_ID", "")
STATE_FILE = "data/state.json"


def http_json(url, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def send(text):
    url = "https://api.telegram.org/bot" + TOKEN + "/sendMessage"
    data = urllib.parse.urlencode({"chat_id": CHAT, "text": text}).encode()
    try:
        http_json(url, data)
        return True
    except Exception as e:
        print("텔레그램 전송 실패:", e)
        return False


def get_candles(coin):
    url = ("https://www.okx.com/api/v5/market/candles?instId="
           + coin + "-USDT-SWAP&bar=1m&limit=6")
    try:
        res = http_json(url)
        rows = []
        for r in res.get("data", []):
            rows.append((int(r[0]), float(r[2]), float(r[3]), float(r[4])))
        rows.sort()
        return rows
    except Exception as e:
        print(coin, "가격 가져오기 실패:", e)
        return []


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def main():
    alerts = load_json("alerts.json", [])
    state = load_json(STATE_FILE, {})
    cache = {}
    keys = set()
    sent_count = 0

    for a in alerts:
        coin = str(a["coin"]).upper().strip()
        price = float(a["price"])
        key = coin + "|" + str(a["price"])
        keys.add(key)

        if coin not in cache:
            cache[coin] = get_candles(coin)
        rows = cache[coin]
        if not rows:
            continue

        last_ts = rows[-1][0]
        last_close = rows[-1][3]
        st = state.get(key)

        if st is None:
            now_state = "above" if last_close >= price else "below"
            state[key] = {"s": now_state, "t": last_ts + 60000}
            print(key, "처음 등록:", now_state)
            continue

        if st["s"] == "below":
            highs = [h for (ts, h, l, c) in rows if ts >= st["t"]]
            if highs and max(highs) >= price:
                msg = ("🔔 [가격 도달] " + coin + " " + format(price, ",")
                       + " 위로 올라옴\n현재가 " + str(last_close)
                       + " | 최근 최고가 " + str(max(highs)))
                if send(msg):
                    st["s"] = "above"
                    st["t"] = last_ts + 60000
                    sent_count += 1
        else:
            if last_close < price:
                st["s"] = "below"
                st["t"] = last_ts + 60000

    for k in list(state.keys()):
        if k not in keys:
            del state[k]

    os.makedirs("data", exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    print("알림 " + str(len(alerts)) + "개 검사, " + str(sent_count) + "건 보냄")


if __name__ == "__main__":
    main()
