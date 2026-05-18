import requests
from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# NSE public API base
NSE_BASE = "https://www.nseindia.com"

# Headers to mimic a browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "application/json, text/plain, */*",
}

# Create a global session that will keep cookies
session = requests.Session()
session.headers.update(HEADERS)

def init_session():
    """Hit NSE homepage once to get required cookies."""
    try:
        session.get(NSE_BASE, timeout=10)
    except:
        pass

# Initialize session at startup
init_session()

# Symbols without any suffix
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
        # Ensure session is fresh (re-initialize cookies if needed)
        init_session()

        # 1. Fetch live quote
        quote_url = f"{NSE_BASE}/api/quote-equity?symbol={symbol.upper()}"
        quote_resp = session.get(quote_url, timeout=10)
        if quote_resp.status_code != 200:
            return jsonify({"error": f"NSE API returned {quote_resp.status_code}"}), 502

        data = quote_resp.json()
        price_info = data.get("priceInfo", {})

        current = float(price_info.get("lastPrice", 0))
        prev_close = float(price_info.get("previousClose", current))
        change = float(price_info.get("change", 0))
        change_pct = float(price_info.get("pChange", 0))
        day_high = float(price_info.get("intraDayHighLow", {}).get("max", 0))
        day_low = float(price_info.get("intraDayHighLow", {}).get("min", 0))
        volume = int(price_info.get("totalTradedVolume", 0))
        name = data.get("info", {}).get("companyName", symbol)

        # 2. Fetch historical data for chart (last 30 days)
        to_date = datetime.now().strftime("%d-%m-%Y")
        from_date = (datetime.now() - timedelta(days=45)).strftime("%d-%m-%Y")  # a bit extra to be safe
        hist_url = f"{NSE_BASE}/api/historical/cm/equity?symbol={symbol.upper()}&series=[%22EQ%22]&from={from_date}&to={to_date}"
        hist_resp = session.get(hist_url, timeout=10)
        history = []
        if hist_resp.status_code == 200:
            hist_json = hist_resp.json()
            records = hist_json.get("data", [])
            # Data is in reverse chronological order; reverse it
            for rec in reversed(records):
                close_price = rec.get("CH_CLOSING_PRICE", rec.get("CH_TRADE_HIGH_PRICE", 0))
                history.append({
                    "date": rec.get("mktDate", rec.get("CH_TIMESTAMP", "")),
                    "close": round(float(close_price), 2) if close_price else 0
                })

        return jsonify({
            "symbol": symbol.upper(),
            "name": name,
            "currentPrice": round(current, 2),
            "previousClose": round(prev_close, 2),
            "change": round(change, 2),
            "changePercent": round(change_pct, 2),
            "dayHigh": round(day_high, 2) if day_high else None,
            "dayLow": round(day_low, 2) if day_low else None,
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
