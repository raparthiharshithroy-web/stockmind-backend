from flask import Flask, jsonify
from flask_cors import CORS
import requests
import os
import yfinance as yf

app = Flask(__name__)
CORS(app)

API_KEY = os.environ.get("MARKETSTACK_KEY", "")
if not API_KEY:
    print("WARNING: MARKETSTACK_KEY not set. /stocks/all will fail.")

SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", "ITC.NS",
    "BAJFINANCE.NS", "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "TITAN.NS", "WIPRO.NS", "HCLTECH.NS", "NTPC.NS",
    "ONGC.NS", "POWERGRID.NS", "ADANIENT.NS", "ADANIPORTS.NS", "JSWSTEEL.NS"
]

STOCK_MAP = {
    "RELIANCE.NS": {"name": "Reliance Industries", "ms_symbol": "RELIANCE.XBOM"},
    "TCS.NS": {"name": "Tata Consultancy Services", "ms_symbol": "TCS.XBOM"},
    "HDFCBANK.NS": {"name": "HDFC Bank", "ms_symbol": "HDFCBANK.XBOM"},
    "INFY.NS": {"name": "Infosys", "ms_symbol": "INFY.XBOM"},
    "ICICIBANK.NS": {"name": "ICICI Bank", "ms_symbol": "ICICIBANK.XBOM"},
    "HINDUNILVR.NS": {"name": "Hindustan Unilever", "ms_symbol": "HINDUNILVR.XBOM"},
    "SBIN.NS": {"name": "State Bank of India", "ms_symbol": "SBIN.XBOM"},
    "BHARTIARTL.NS": {"name": "Bharti Airtel", "ms_symbol": "BHARTIARTL.XBOM"},
    "KOTAKBANK.NS": {"name": "Kotak Mahindra Bank", "ms_symbol": "KOTAKBANK.XBOM"},
    "ITC.NS": {"name": "ITC Limited", "ms_symbol": "ITC.XBOM"},
    "BAJFINANCE.NS": {"name": "Bajaj Finance", "ms_symbol": "BAJFINANCE.XBOM"},
    "LT.NS": {"name": "Larsen & Toubro", "ms_symbol": "LT.XBOM"},
    "AXISBANK.NS": {"name": "Axis Bank", "ms_symbol": "AXISBANK.XBOM"},
    "ASIANPAINT.NS": {"name": "Asian Paints", "ms_symbol": "ASIANPAINT.XBOM"},
    "MARUTI.NS": {"name": "Maruti Suzuki", "ms_symbol": "MARUTI.XBOM"},
    "SUNPHARMA.NS": {"name": "Sun Pharmaceutical", "ms_symbol": "SUNPHARMA.XBOM"},
    "TITAN.NS": {"name": "Titan Company", "ms_symbol": "TITAN.XBOM"},
    "WIPRO.NS": {"name": "Wipro", "ms_symbol": "WIPRO.XBOM"},
    "HCLTECH.NS": {"name": "HCL Technologies", "ms_symbol": "HCLTECH.XBOM"},
    "NTPC.NS": {"name": "NTPC Limited", "ms_symbol": "NTPC.XBOM"},
    "ONGC.NS": {"name": "Oil & Natural Gas Corporation", "ms_symbol": "ONGC.XBOM"},
    "POWERGRID.NS": {"name": "Power Grid Corporation", "ms_symbol": "POWERGRID.XBOM"},
    "ADANIENT.NS": {"name": "Adani Enterprises", "ms_symbol": "ADANIENT.XBOM"},
    "ADANIPORTS.NS": {"name": "Adani Ports & SEZ", "ms_symbol": "ADANIPORTS.XBOM"},
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
    return jsonify([s.replace(".NS", "") for s in SYMBOLS])

@app.route('/stocks/all')
def get_all_stocks():
    if not API_KEY:
        return jsonify({"error": "Marketstack API key not configured."}), 500

    try:
        ms_symbols = [STOCK_MAP[s]["ms_symbol"] for s in SYMBOLS if s in STOCK_MAP]
        symbols_param = ",".join(ms_symbols)

        eod_url = f"{BASE_URL}/tickers/{symbols_param}/eod/latest"
        resp = requests.get(eod_url, params={"access_key": API_KEY})
        data = resp.json()

        if "error" in data:
            return jsonify({"error": data["error"]["message"]}), 500

        eod_list = data.get("data", [])
        eod_lookup = {item['symbol']: item for item in eod_list}

        all_stock_data = []
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
                "history": []
            })

        return jsonify(all_stock_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stock/<symbol>')
def get_stock_history(symbol):
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
