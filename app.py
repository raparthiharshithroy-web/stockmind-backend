from flask import Flask, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# Free, no‑key Indian Stock Market API
BASE_URL = "http://65.0.104.9"

SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "SBIN", "BHARTIARTL", "KOTAKBANK", "ITC",
    "BAJFINANCE", "LT", "AXISBANK", "ASIANPAINT", "MARUTI",
    "SUNPHARMA", "TITAN", "WIPRO", "HCLTECH", "NTPC",
    "ONGC", "POWERGRID", "ADANIENT", "ADANIPORTS", "JSWSTEEL"
]

@app.route('/')
def home():
    return jsonify({"status": "ok", "endpoints": ["/health", "/symbols", "/stock/<symbol>"]})

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/symbols')
def get_symbols():
    return jsonify(SYMBOLS)

@app.route('/stock/<symbol>')
def get_stock(symbol):
    try:
        # 1. Get quote
        quote_resp = requests.get(f"{BASE_URL}/stock?symbol={symbol}&res=num")
        quote_data = quote_resp.json()

        if quote_data.get("status") != "success":
            return jsonify({"error": quote_data.get("message", "Unknown error")}), 400

        data = quote_data.get("data", {})
        current = float(data.get("last_price", 0))
        prev_close = float(data.get("previous_close", current))
        change = float(data.get("change", 0))
        change_pct = float(data.get("percent_change", 0))
        high = float(data.get("day_high", 0))
        low = float(data.get("day_low", 0))
        volume = int(data.get("volume", 0))
        name = data.get("company_name", symbol)

        # 2. Get 30‑day chart data
        history = []
        hist_resp = requests.get(f"{BASE_URL}/history?symbol={symbol}&range=1mo")
        if hist_resp.status_code == 200:
            hist_data = hist_resp.json()
            if "data" in hist_data:
                for day in hist_data["data"]:
                    history.append({
                        "date": day.get("date", ""),
                        "close": round(float(day.get("close", 0)), 2)
                    })
                history.reverse()  # oldest first

        return jsonify({
            "symbol": symbol,
            "name": name,
            "currentPrice": round(current, 2),
            "previousClose": round(prev_close, 2),
            "change": round(change, 2),
            "changePercent": round(change_pct, 2),
            "dayHigh": round(high, 2) if high else None,
            "dayLow": round(low, 2) if low else None,
            "volume": volume if volume else None,
            "marketCap": None,
            "pe": None,
            "sector": "N/A",
            "history": history
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
