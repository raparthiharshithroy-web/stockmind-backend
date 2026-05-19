from flask import Flask, jsonify
from flask_cors import CORS
import requests
import os
import yfinance as yf

app = Flask(__name__)
CORS(app)

API_KEY = os.environ.get("MARKETSTACK_KEY", "")

SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", "ITC.NS",
    "BAJFINANCE.NS", "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "TITAN.NS", "WIPRO.NS", "HCLTECH.NS", "NTPC.NS",
    "ONGC.NS", "POWERGRID.NS", "ADANIENT.NS", "ADANIPORTS.NS", "JSWSTEEL.NS"
]

STOCK_MAP = {
    "RELIANCE.NS":  {"name": "Reliance Industries",           "ms_symbol": "RELIANCE.XBOM"},
    "TCS.NS":       {"name": "Tata Consultancy Services",     "ms_symbol": "TCS.XBOM"},
    "HDFCBANK.NS":  {"name": "HDFC Bank",                     "ms_symbol": "HDFCBANK.XBOM"},
    "INFY.NS":      {"name": "Infosys",                       "ms_symbol": "INFY.XBOM"},
    "ICICIBANK.NS": {"name": "ICICI Bank",                    "ms_symbol": "ICICIBANK.XBOM"},
    "HINDUNILVR.NS":{"name": "Hindustan Unilever",            "ms_symbol": "HINDUNILVR.XBOM"},
    "SBIN.NS":      {"name": "State Bank of India",           "ms_symbol": "SBIN.XBOM"},
    "BHARTIARTL.NS":{"name": "Bharti Airtel",                 "ms_symbol": "BHARTIARTL.XBOM"},
    "KOTAKBANK.NS": {"name": "Kotak Mahindra Bank",           "ms_symbol": "KOTAKBANK.XBOM"},
    "ITC.NS":       {"name": "ITC Limited",                   "ms_symbol": "ITC.XBOM"},
    "BAJFINANCE.NS":{"name": "Bajaj Finance",                 "ms_symbol": "BAJFINANCE.XBOM"},
    "LT.NS":        {"name": "Larsen & Toubro",               "ms_symbol": "LT.XBOM"},
    "AXISBANK.NS":  {"name": "Axis Bank",                     "ms_symbol": "AXISBANK.XBOM"},
    "ASIANPAINT.NS":{"name": "Asian Paints",                  "ms_symbol": "ASIANPAINT.XBOM"},
    "MARUTI.NS":    {"name": "Maruti Suzuki",                 "ms_symbol": "MARUTI.XBOM"},
    "SUNPHARMA.NS": {"name": "Sun Pharmaceutical",            "ms_symbol": "SUNPHARMA.XBOM"},
    "TITAN.NS":     {"name": "Titan Company",                 "ms_symbol": "TITAN.XBOM"},
    "WIPRO.NS":     {"name": "Wipro",                         "ms_symbol": "WIPRO.XBOM"},
    "HCLTECH.NS":   {"name": "HCL Technologies",              "ms_symbol": "HCLTECH.XBOM"},
    "NTPC.NS":      {"name": "NTPC Limited",                  "ms_symbol": "NTPC.XBOM"},
    "ONGC.NS":      {"name": "Oil & Natural Gas Corporation", "ms_symbol": "ONGC.XBOM"},
    "POWERGRID.NS": {"name": "Power Grid Corporation",        "ms_symbol": "POWERGRID.XBOM"},
    "ADANIENT.NS":  {"name": "Adani Enterprises",             "ms_symbol": "ADANIENT.XBOM"},
    "ADANIPORTS.NS":{"name": "Adani Ports & SEZ",             "ms_symbol": "ADANIPORTS.XBOM"},
    "JSWSTEEL.NS":  {"name": "JSW Steel",                     "ms_symbol": "JSWSTEEL.XBOM"}
}

def fetch_batch():
    """Shared helper — fetches all 25 stocks from Marketstack and returns a list."""
    ms_symbols = [STOCK_MAP[s]["ms_symbol"] for s in SYMBOLS if s in STOCK_MAP]
    resp = requests.get(
        "https://api.marketstack.com/v1/eod/latest",
        params={
            "access_key": API_KEY,
            "symbols": ",".join(ms_symbols),
            "limit": 25
        },
        timeout=15
    )
    raw = resp.json()
    if "error" in raw:
        raise Exception(str(raw["error"]))

    eod_lookup = {item["symbol"]: item for item in raw.get("data", [])}

    result = []
    for sym in SYMBOLS:
        if sym not in STOCK_MAP:
            continue
        ms_sym = STOCK_MAP[sym]["ms_symbol"]
        eod    = eod_lookup.get(ms_sym, {})

        close  = float(eod.get("close")      or 0)
        adj    = float(eod.get("adj_close")  or close)
        change = float(eod.get("change")     or 0)
        chgpct = float(eod.get("change_pct") or 0)

        result.append({
            "symbol":        sym.replace(".NS", ""),
            "name":          STOCK_MAP[sym]["name"],
            "currentPrice":  round(close,  2),
            "previousClose": round(adj,    2),
            "change":        round(change, 2),
            "changePercent": round(chgpct, 2),
            "dayHigh":       round(float(eod.get("high") or 0), 2) or None,
            "dayLow":        round(float(eod.get("low")  or 0), 2) or None,
            "volume":        int(eod.get("volume") or 0) or None,
            "marketCap":     None,
            "pe":            None,
            "sector":        "N/A",
            "history":       []
        })
    return result


# ── existing routes ────────────────────────────────────────────────────────────

@app.route('/')
def home():
    return jsonify({"status": "ok", "endpoints": [
        "/health", "/symbols", "/batch",
        "/top-gainers", "/top-losers",
        "/stock/<symbol>"
    ]})

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/symbols')
def get_symbols():
    return jsonify([s.replace(".NS", "") for s in SYMBOLS])

@app.route('/batch')
def get_all_stocks():
    if not API_KEY:
        return jsonify({"error": "MARKETSTACK_KEY not set on Render"}), 500
    try:
        return jsonify(fetch_batch())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── NEW: top gainers & losers ─────────────────────────────────────────────────

@app.route('/top-gainers')
def top_gainers():
    """Top 5 stocks by % change today."""
    if not API_KEY:
        return jsonify({"error": "MARKETSTACK_KEY not set on Render"}), 500
    try:
        stocks = fetch_batch()
        gainers = sorted(stocks, key=lambda x: x["changePercent"], reverse=True)[:5]
        return jsonify(gainers)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/top-losers')
def top_losers():
    """Bottom 5 stocks by % change today."""
    if not API_KEY:
        return jsonify({"error": "MARKETSTACK_KEY not set on Render"}), 500
    try:
        stocks = fetch_batch()
        losers = sorted(stocks, key=lambda x: x["changePercent"])[:5]
        return jsonify(losers)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── existing: stock history ───────────────────────────────────────────────────

@app.route('/stock/<symbol>')
def get_stock_history(symbol):
    try:
        ticker = yf.Ticker(symbol.upper() + ".NS")
        hist   = ticker.history(period="1mo")
        if hist.empty:
            return jsonify({"error": f"No data for {symbol}"}), 404
        history = [
            {"date": str(d.date()), "close": round(row['Close'], 2)}
            for d, row in hist.iterrows()
        ]
        return jsonify({"symbol": symbol.upper(), "history": history})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
