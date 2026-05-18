from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# Your Alpha Vantage API key — you'll set this in Render environment variable later
API_KEY = os.environ.get("ALPHA_VANTAGE_KEY", "")

SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", "ITC.NS",
    "BAJFINANCE.NS", "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "TITAN.NS", "WIPRO.NS", "HCLTECH.NS", "NTPC.NS",
    "ONGC.NS", "POWERGRID.NS", "ADANIENT.NS", "ADANIPORTS.NS", "JSWSTEEL.NS"
]

BASE_URL = "https://www.alphavantage.co/query"

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
        return jsonify({"error": "Alpha Vantage API key not configured. Set ALPHA_VANTAGE_KEY environment variable."}), 500

    try:
        # Get current quote
        quote_params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol.replace(".NS", ".NS"),  # keep as is
            "apikey": API_KEY
        }
        quote_resp = requests.get(BASE_URL, params=quote_params)
        quote_data = quote_resp.json()

        if "Global Quote" not in quote_data or not quote_data["Global Quote"]:
            return jsonify({"error": f"No quote data for {symbol}"}), 404

        global_quote = quote_data["Global Quote"]
        current_price = float(global_quote.get("05. price", 0))
        previous_close = float(global_quote.get("08. previous close", current_price))
        change = float(global_quote.get("09. change", 0))
        change_pct_str = global_quote.get("10. change percent", "0%").replace("%", "")
        change_pct = float(change_pct_str)

        # Get daily time series for chart (last 30 days)
        daily_params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "apikey": API_KEY,
            "outputsize": "compact"  # last 100 days
        }
        daily_resp = requests.get(BASE_URL, params=daily_params)
        daily_data = daily_resp.json()

        history = []
        if "Time Series (Daily)" in daily_data:
            time_series = daily_data["Time Series (Daily)"]
            # Take last 30 days
            sorted_dates = sorted(time_series.keys(), reverse=True)[:30]
            for date in sorted_dates:
                day_data = time_series[date]
                history.append({
                    "date": date,
                    "close": round(float(day_data["4. close"]), 2)
                })
            history.reverse()  # chronological order

        data = {
            "symbol": symbol,
            "name": symbol.replace(".NS", ""),
            "currentPrice": round(current_price, 2),
            "previousClose": round(previous_close, 2),
            "change": round(change, 2),
            "changePercent": round(change_pct, 2),
            "dayHigh": float(global_quote.get("03. high", 0)) or None,
            "dayLow": float(global_quote.get("04. low", 0)) or None,
            "volume": int(global_quote.get("06. volume", 0)) or None,
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
