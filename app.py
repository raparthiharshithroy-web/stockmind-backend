from flask import Flask, jsonify, request
from flask_cors import CORS
from jugaad_data.nse import NSELive, stock_df
from datetime import date, timedelta
import os
import requests

app = Flask(__name__)
CORS(app)

n = NSELive()

# --- Configuration ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")   # Set in Render Environment
if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY not set. Portfolio AI endpoint will fail.")

# --- Symbols list ---
SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "SBIN", "BHARTIARTL", "KOTAKBANK", "ITC",
    "BAJFINANCE", "LT", "AXISBANK", "ASIANPAINT", "MARUTI",
    "SUNPHARMA", "TITAN", "WIPRO", "HCLTECH", "NTPC",
    "ONGC", "POWERGRID", "ADANIENT", "ADANIPORTS", "JSWSTEEL"
]

# --- Helper functions ---
def fetch_one(symbol):
    """Fetch core metrics for a single symbol (used by batch and overview)."""
    try:
        q = n.stock_quote(symbol)
        info = q.get("priceInfo", {})
        meta = q.get("info", {})
        wk   = info.get("weekHighLow", {})
        trade_info = q.get("marketDeptOrderBook", {}).get("tradeInfo", {})
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
            "volume":        trade_info.get("totalTradedVolume"),
            "sector":        meta.get("industry", "N/A"),
            # Additional fields for overview:
            "pe":            info.get("pe"),                       # PE ratio if available
            "issuedSize":    meta.get("issuedSize"),               # total shares
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}

def fetch_all():
    """Fetch core data for all 25 symbols."""
    return [fetch_one(s) for s in SYMBOLS]


# ==============================================
# ROUTES
# ==============================================

@app.route('/')
def home():
    return jsonify({
        "status": "ok",
        "endpoints": [
            "/health",
            "/batch",
            "/top-gainers",
            "/top-losers",
            "/stock/<symbol>",
            "/stock/<symbol>/overview",
            "/sector-performance",
            "/portfolio/analyze (POST)"
        ]
    })

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
    """Get full detail for a single stock including 30-day history."""
    try:
        sym = symbol.upper()
        q   = n.stock_quote(sym)
        info = q.get("priceInfo", {})
        meta = q.get("info", {})
        wk   = info.get("weekHighLow", {})

        # historical data via jugaad
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

@app.route('/stock/<symbol>/overview')
def stock_overview(symbol):
    """Deeper metrics: PE, market cap, 52-week range, etc."""
    try:
        data = fetch_one(symbol.upper())
        if "error" in data:
            return jsonify({"error": data["error"]}), 404

        # calculate market cap if issued size is available
        market_cap = None
        issued = data.get("issuedSize")
        price  = data.get("currentPrice")
        if issued and price:
            try:
                market_cap = round(float(issued) * float(price), 2)
            except:
                pass

        overview = {
            "symbol":        data["symbol"],
            "name":          data["name"],
            "sector":        data["sector"],
            "currentPrice":  data["currentPrice"],
            "change":        data["change"],
            "changePercent": data["changePercent"],
            "dayHigh":       data["dayHigh"],
            "dayLow":        data["dayLow"],
            "week52High":    data["week52High"],
            "week52Low":     data["week52Low"],
            "volume":        data["volume"],
            "pe":            data.get("pe"),
            "marketCap":     market_cap
        }
        return jsonify(overview)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/sector-performance')
def sector_performance():
    """Group stocks by sector and show average % change."""
    try:
        all_stocks = fetch_all()
        sectors = {}
        for stock in all_stocks:
            if "error" in stock or stock.get("changePercent") is None:
                continue
            sector = stock["sector"]
            if sector not in sectors:
                sectors[sector] = {"count": 0, "total_change": 0.0}
            sectors[sector]["count"] += 1
            sectors[sector]["total_change"] += float(stock["changePercent"])

        result = []
        for sector, data in sectors.items():
            avg = round(data["total_change"] / data["count"], 2)
            result.append({
                "sector": sector,
                "avgChangePercent": avg,
                "stockCount": data["count"]
            })
        result.sort(key=lambda x: x["avgChangePercent"], reverse=True)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/portfolio/analyze', methods=['POST'])
def portfolio_analyze():
    """Accept portfolio holdings and return AI analysis."""
    if not GROQ_API_KEY:
        return jsonify({"error": "GROQ_API_KEY not configured on server."}), 500

    data = request.get_json()
    if not data or "holdings" not in data:
        return jsonify({"error": "Invalid payload. Expected {'holdings': [...]}"}), 400

    holdings = data["holdings"]
    try:
        portfolio_data = []
        total_current_value = 0
        total_invested = 0

        for h in holdings:
            sym = h["symbol"].upper()
            qty = float(h.get("quantity", 0))
            buy_price = float(h.get("buyPrice", 0))
            quote = n.stock_quote(sym)
            if not quote:
                continue
            current_price = float(quote["priceInfo"]["lastPrice"])
            current_value = current_price * qty
            invested = buy_price * qty
            pnl = current_value - invested
            pnl_pct = (pnl / invested) * 100 if invested else 0

            portfolio_data.append({
                "symbol": sym,
                "quantity": qty,
                "buyPrice": buy_price,
                "currentPrice": current_price,
                "currentValue": round(current_value, 2),
                "invested": round(invested, 2),
                "pnl": round(pnl, 2),
                "pnlPercent": round(pnl_pct, 2)
            })
            total_current_value += current_value
            total_invested += invested

        overall_pnl = total_current_value - total_invested
        overall_pnl_pct = (overall_pnl / total_invested * 100) if total_invested else 0

        # Build Groq prompt
        prompt = f"""You are a portfolio advisor. Analyze this Indian stock portfolio and give a brief summary, risk assessment, and suggestions for rebalancing (max 150 words).
Portfolio details:
{portfolio_data}
Total current value: ₹{round(total_current_value, 2)}
Total invested: ₹{round(total_invested, 2)}
Overall P&L: ₹{round(overall_pnl, 2)} ({round(overall_pnl_pct,2)}%)
"""

        # Call Groq
        groq_resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.3
            }
        )
        groq_data = groq_resp.json()
        ai_analysis = groq_data.get("choices", [{}])[0].get("message", {}).get("content", "AI analysis unavailable.")

        return jsonify({
            "holdings": portfolio_data,
            "totalCurrentValue": round(total_current_value, 2),
            "totalInvested": round(total_invested, 2),
            "overallPnL": round(overall_pnl, 2),
            "overallPnLPercent": round(overall_pnl_pct, 2),
            "aiAnalysis": ai_analysis
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
