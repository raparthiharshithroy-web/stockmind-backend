from flask import Flask, jsonify
from flask_cors import CORS
from jugaad_data.nse import NSELive

app = Flask(__name__)
CORS(app)

n = NSELive()

SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "SBIN", "BHARTIARTL", "KOTAKBANK", "ITC",
    "BAJFINANCE", "LT", "AXISBANK", "ASIANPAINT", "MARUTI",
    "SUNPHARMA", "TITAN", "WIPRO", "HCLTECH", "NTPC",
    "ONGC", "POWERGRID", "ADANIENT", "ADANIPORTS", "JSWSTEEL"
]

def fetch_one(symbol):
    try:
        q = n.stock_quote(symbol)
        info = q.get("priceInfo", {})
        meta = q.get("info", {})
        wk   = q.get("priceInfo", {}).get("weekHighLow", {})
        return {
            "symbol":        symbol,
            "name":          meta.get("companyName", symbol),
            "currentPrice":  info.get("lastPrice"),
            "previousClose": info.get("previousClose"),
            "change":        info.get("change"),
            "changePercent": info.get("pChange"),
            "dayHigh":       info.get("intraDayHighLow", {}).get("max"),
            "dayLow":        info.get("intraDayHighLow", {}).get("min"),
            "week52High":    wk.get("max"),
            "week52Low":     wk.get("min"),
            "volume":        q.get("marketDeptOrderBook", {}).get("tradeInfo", {}).get("totalTradedVolume"),
            "sector":        meta.get("industry", "N/A"),
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}

def fetch_all():
    return [fetch_one(s) for s in SYMBOLS]


@app.route('/')
def home():
    return jsonify({"status": "ok", "endpoints": [
        "/health", "/batch", "/top-gainers", "/top-losers", "/stock/<symbol>"
    ]})

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/batch')
def batch():
    try:
        return jsonify(fetch_all())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/top-gainers')
def top_gainers():
    try:
        stocks = [s for s in fetch_all() if "error" not in s and s.get("changePercent") is not None]
        return jsonify(sorted(stocks, key=lambda x: x["changePercent"], reverse=True)[:5])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/top-losers')
def top_losers():
    try:
        stocks = [s for s in fetch_all() if "error" not in s and s.get("changePercent") is not None]
        return jsonify(sorted(stocks, key=lambda x: x["changePercent"])[:5])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stock/<symbol>')
def stock_detail(symbol):
    try:
        sym = symbol.upper()
        q   = n.stock_quote(sym)
        info = q.get("priceInfo", {})
        meta = q.get("info", {})
        wk   = info.get("weekHighLow", {})

        # historical via jugaad
        from datetime import date, timedelta
        from jugaad_data.nse import stock_df
        end   = date.today()
        start = end - timedelta(days=30)
        df = stock_df(symbol=sym, from_date=start, to_date=end, series="EQ")
        history = []
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                history.append({
                    "date":  str(row.get("DATE", "")),
                    "close": round(float(row.get("CLOSE", 0)), 2)
                })

        return jsonify({
            "symbol":        sym,
            "name":          meta.get("companyName", sym),
            "currentPrice":  info.get("lastPrice"),
            "previousClose": info.get("previousClose"),
            "change":        info.get("change"),
            "changePercent": info.get("pChange"),
            "dayHigh":       info.get("intraDayHighLow", {}).get("max"),
            "dayLow":        info.get("intraDayHighLow", {}).get("min"),
            "week52High":    wk.get("max"),
            "week52Low":     wk.get("min"),
            "sector":        meta.get("industry", "N/A"),
            "history":       history
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
