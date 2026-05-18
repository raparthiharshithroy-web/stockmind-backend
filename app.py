from flask import Flask, jsonify
from flask_cors import CORS
import requests
import os
import time

app = Flask(__name__)
CORS(app)

API_KEY = os.environ.get("ALPHA_VANTAGE_KEY", "")

# Alpha Vantage free tier uses .BSE suffix for BSE stocks
SYMBOLS = [
    "RELIANCE.BSE", "TCS.BSE", "HDFCBANK.BSE", "INFY.BSE", "ICICIBANK.BSE",
    "HINDUNILVR.BSE", "SBIN.BSE", "BHARTIARTL.BSE", "KOTAKBANK.BSE", "ITC.BSE",
    "BAJFINANCE.BSE", "LT.BSE", "AXISBANK.BSE", "ASIANPAINT.BSE", "MARUTI.BSE",
    "SUNPHARMA.BSE", "TITAN.BSE", "WIPRO.BSE", "HCLTECH.BSE", "NTPC.BSE",
    "ONGC.BSE", "POWERGRID.BSE", "ADANIENT.BSE", "ADANIPORTS.BSE", "JSWSTEEL.BSE"
]

# Display names for stocks
SYMBOL_NAMES = {
    "RELIANCE.BSE": "Reliance Industries",
    "TCS.BSE": "Tata Consultancy Services",
    "HDFCBANK.BSE": "HDFC Bank",
    "INFY.BSE": "Infosys",
    "ICICIBANK.BSE": "ICICI Bank",
    "HINDUNILVR.BSE": "Hindustan Unilever",
    "SBIN.BSE": "State Bank of India",
    "BHARTIARTL.BSE": "Bharti Airtel",
    "KOTAKBANK.BSE": "Kotak Mahindra Bank",
    "ITC.BSE": "ITC Limited",
    "BAJFINANCE.BSE": "Bajaj Finance",
    "LT.BSE": "Larsen & Toubro",
    "AXISBANK.BSE": "Axis Bank",
    "ASIANPAINT.BSE": "Asian Paints",
    "MARUTI.BSE": "Maruti Suzuki",
    "SUNPHARMA.BSE": "Sun Pharmaceutical",
    "TITAN.BSE": "Titan Company",
    "WIPRO.BSE": "Wipro",
    "HCLTECH.BSE": "HCL Technologies",
    "NTPC.BSE": "NTPC Limited",
    "ONGC.BSE": "Oil & Natural Gas Corporation",
    "POWERGRID.BSE": "Power Grid Corporation",
    "ADANIENT.BSE": "Adani Enterprises",
    "ADANIPORTS.BSE": "Adani Ports & SEZ",
    "JSWSTEEL.BSE": "JSW Steel"
}

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
        return jsonify({"error": "Alpha Vantage API key not configured. Set ALPHA_VANTAGE_KEY."}), 500

    try:
        # Alpha Vantage free tier allows 5 calls per minute – we'll rely on frontend to pace,
        # but we can add a tiny delay if needed later.

        # Get quote
        quote_params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": API_KEY
        }
        quote_resp = requests.get(BASE_URL, params=quote_params)
        quote_data = quote_resp.json()

        if "Global Quote" not in quote_data or not quote_data["Global Quote"]:
            return jsonify({"error": f"No quote data for {symbol}. Check if the symbol is correct or API limit reached."}), 404

        global_quote = quote_data["Global Quote"]
        current = float(global_quote.get("05. price", 0))
        prev_close = float(global_quote.get("08. previous close", current))
        change = float(global_quote.get("09. change", 0))
        change_pct_str = global_quote.get("10. change percent", "0%").replace("%", "")
        change_pct = float(change_pct_str)
        high = float(global_quote.get("03. high", 0))
        low = float(global_quote.get("04. low", 0))
        volume = int(global_quote.get("06. volume", 0))
        name = SYMBOL_NAMES.get(symbol, symbol.replace(".BSE", ""))

        # Get daily time series for chart (compact = last 100 days)
        daily_params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "apikey": API_KEY,
            "outputsize": "compact"
        }
        daily_resp = requests.get(BASE_URL, params=daily_params)
        daily_data = daily_resp.json()

        history = []
        if "Time Series (Daily)" in daily_data:
            time_series = daily_data["Time Series (Daily)"]
            sorted_dates = sorted(time_series.keys(), reverse=True)[:30]
            for date in sorted_dates:
                day_data = time_series[date]
                history.append({
                    "date": date,
                    "close": round(float(day_data["4. close"]), 2)
                })
            history.reverse()

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
