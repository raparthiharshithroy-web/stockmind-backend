from flask import Flask, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

API_KEY = os.environ.get("TWELVE_DATA_KEY", "")

SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", "ITC.NS",
    "BAJFINANCE.NS", "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "TITAN.NS", "WIPRO.NS", "HCLTECH.NS", "NTPC.NS",
    "ONGC.NS", "POWERGRID.NS", "ADANIENT.NS", "ADANIPORTS.NS", "JSWSTEEL.NS"
]

BASE_URL = "https://api.twelvedata.com"

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
    if not API_KEY:
        return jsonify({"error": "Twelve Data API key not configured. Set TWELVE_DATA_KEY."}), 500

    try:
        # Get quote
        quote_url = f"{BASE_URL}/quote?symbol={symbol}&apikey={API_KEY}"
        quote_resp = requests.get(quote_url)
        quote_data = quote_resp.json()

        if "code" in quote_data and quote_data["code"] != 200:
            return jsonify({"error": quote_data.get("message", "Unknown error")}), 400

        current = float(quote_data.get("close", 0))
        prev_close = float(quote_data.get("previous_close", current))
        change = float(quote_data.get("change", 0))
        change_pct = float(quote_data.get("percent_change", 0))
        high = float(quote_data.get("high", 0))
        low = float(quote_data.get("low", 0))
        volume = int(quote_data.get("volume", 0))
        name = quote_data.get("name", symbol.replace(".NS", ""))

        # Get 30-day chart data
        timeseries_url = f"{BASE_URL}/time_series?symbol={symbol}&interval=1day&outputsize=30&apikey={API_KEY}"
        ts_resp = requests.get(timeseries_url)
        ts_data = ts_resp.json()

        history = []
        if "values" in ts_data:
            for day in ts_data["values"]:
                history.append({
                    "date": day["datetime"],
                    "close": round(float(day["close"]), 2)
                })
            history.reverse()  # oldest first

        data = {
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
        }
        return jsonify(data)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
