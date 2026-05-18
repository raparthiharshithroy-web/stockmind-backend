from flask import Flask, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

API_KEY = os.environ.get("ALPHA_VANTAGE_KEY", "")

# Alpha Vantage free tier uses .BO suffix for BSE stocks
SYMBOLS = [
    "RELIANCE.BO", "TCS.BO", "HDFCBANK.BO", "INFY.BO", "ICICIBANK.BO",
    "HINDUNILVR.BO", "SBIN.BO", "BHARTIARTL.BO", "KOTAKBANK.BO", "ITC.BO",
    "BAJFINANCE.BO", "LT.BO", "AXISBANK.BO", "ASIANPAINT.BO", "MARUTI.BO",
    "SUNPHARMA.BO", "TITAN.BO", "WIPRO.BO", "HCLTECH.BO", "NTPC.BO",
    "ONGC.BO", "POWERGRID.BO", "ADANIENT.BO", "ADANIPORTS.BO", "JSWSTEEL.BO"
]

# Display names for stocks
SYMBOL_NAMES = {
    "RELIANCE.BO": "Reliance Industries",
    "TCS.BO": "Tata Consultancy Services",
    "HDFCBANK.BO": "HDFC Bank",
    "INFY.BO": "Infosys",
    "ICICIBANK.BO": "ICICI Bank",
    "HINDUNILVR.BO": "Hindustan Unilever",
    "SBIN.BO": "State Bank of India",
    "BHARTIARTL.BO": "Bharti Airtel",
    "KOTAKBANK.BO": "Kotak Mahindra Bank",
    "ITC.BO": "ITC Limited",
    "BAJFINANCE.BO": "Bajaj Finance",
    "LT.BO": "Larsen & Toubro",
    "AXISBANK.BO": "Axis Bank",
    "ASIANPAINT.BO": "Asian Paints",
    "MARUTI.BO": "Maruti Suzuki",
    "SUNPHARMA.BO": "Sun Pharmaceutical",
    "TITAN.BO": "Titan Company",
    "WIPRO.BO": "Wipro",
    "HCLTECH.BO": "HCL Technologies",
    "NTPC.BO": "NTPC Limited",
    "ONGC.BO": "Oil & Natural Gas Corporation",
    "POWERGRID.BO": "Power Grid Corporation",
    "ADANIENT.BO": "Adani Enterprises",
    "ADANIPORTS.BO": "Adani Ports & SEZ",
    "JSWSTEEL.BO": "JSW Steel"
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
        name = SYMBOL_NAMES.get(symbol, symbol.replace(".BO", ""))

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
