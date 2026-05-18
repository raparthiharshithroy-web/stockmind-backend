from flask import Flask, jsonify
from flask_cors import CORS
import requests
import os
import yfinance as yf

app = Flask(__name__)
CORS(app)

# --- Configuration ---
API_KEY = os.environ.get("MARKETSTACK_KEY", "")
if not API_KEY:
    print("WARNING: MARKETSTACK_KEY environment variable not set. /stocks/all will fail.")

# List of NSE symbols for Yahoo Finance
SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", "ITC.NS",
    "BAJFINANCE.NS", "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "TITAN.NS", "WIPRO.NS", "HCLTECH.NS", "NTPC.NS",
    "ONGC.NS", "POWERGRID.NS", "ADANIENT.NS", "ADANIPORTS.NS", "JSWSTEEL.NS"
]

# Mapping from Yahoo symbol to company name and Marketstack symbol
STOCK_MAP = {
    "RELIANCE.NS": {"name": "Reliance Industries", "ms_symbol": "RELIANCE.XBOM"},
    "TCS.NS": {"name": "Tata Consultancy Services", "ms_symbol": "TCS.XBOM"},
    # ... (The rest of the mapping is the same as before, just add the rest here)
    "JSWSTEEL.NS": {"name": "JSW Steel", "ms_symbol": "JSWSTEEL.XBOM"}
}

BASE_URL = "https://api.marketstack.com/v1"

@app.route('/')
def home():
    return jsonify({"status": "ok", "endpoints": ["/health", "/symbols", "/stocks/all", "/stock/<symbol>"]})

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/symbols')
def get_symbols():
    # Return only the display symbols (e.g., "RELIANCE")
    return jsonify([s.replace(".NS", "") for s in SYMBOLS])

@app.route('/stocks/all')
def get_all_stocks():
    """Fetch latest EOD data for all stocks using a single Marketstack API call."""
    if not API_KEY:
        return jsonify({"error": "Marketstack API key not configured."}), 500

    try:
        # Get all Marketstack symbols
        ms_symbols = [STOCK_MAP[s]["ms_symbol"] for s in SYMBOLS if s in STOCK_MAP]
        symbols_param = ",".join(ms_symbols)

        # Make a SINGLE API call for all latest EOD data
        eod_url = f"{BASE_URL}/tickers/{symbols_param}/eod/latest"
        resp = requests.get(eod_url, params={"access_key": API_KEY})
        data = resp.json()

        if "error" in data:
            return jsonify({"error": data["error"]["message"]}), 500

        all_stock_data = []
        # The response contains a 'data' key which is a list of stock objects
        eod_list = data.get("data", [])
        
        # Create a lookup for quick access
        eod_lookup = {item['symbol']: item for item in eod_list}

        for sym in SYMBOLS:
            if sym not in STOCK_MAP:
                continue
            ms_sym = STOCK_MAP[sym]["ms_symbol"]
            name = STOCK_MAP[sym]["name"]
            eod = eod_lookup.get(ms_sym, {})

            current_price = eod.get("close", 0)
            prev_close = eod.get("previous_close", current_price)
            change = eod.get("change", 0)
            change_pct = eod.get("change_pct", 0)
            high = eod.get("high", 0)
            low = eod.get("low", 0)
            volume = eod.get("volume", 0)

            all_stock_data.append({
                "symbol": sym.replace(".NS", ""),
                "name": name,
                "currentPrice": round(float(current_price), 2),
                "previousClose": round(float(prev_close), 2),
                "change": round(float(change), 2),
                "changePercent": round(float(change_pct), 2),
                "dayHigh": round(float(high), 2) if high else None,
                "dayLow": round(float(low), 2) if low else None,
                "volume": int(volume) if volume else None,
                "marketCap": None,
                "pe": None,
                "sector": "N/A",
                "history": [] # History will be fetched separately
            })
            
        return jsonify(all_stock_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stock/<symbol>')
def get_stock_history(symbol):
    """Fetch historical chart data for a single stock using yfinance."""
    try:
        ticker_symbol = symbol.upper() + ".NS"
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="1mo")
        if hist.empty:
            return jsonify({"error": f"No historical data for {ticker_symbol}"}), 404

        history = [
            {"date": str(d.date()), "close": round(row['Close'], 2)}
            for d, row in hist.iterrows()
        ]
        return jsonify({"symbol": symbol.upper(), "history": history})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
