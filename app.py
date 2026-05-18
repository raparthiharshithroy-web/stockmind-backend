from flask import Flask, jsonify
from flask_cors import CORS
import yfinance as yf

app = Flask(__name__)
CORS(app)  # Allow all origins — required for local HTML file access

NSE_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS",
    "LT.NS", "BAJFINANCE.NS", "ASIANPAINT.NS", "AXISBANK.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "NESTLEIND.NS", "ULTRACEMCO.NS", "WIPRO.NS", "HCLTECH.NS",
    "TITAN.NS", "POWERGRID.NS", "NTPC.NS", "TECHM.NS", "ADANIENT.NS"
]

def safe_val(val, fallback=None):
    """Return None-safe value from yfinance info dict."""
    if val is None:
        return fallback
    try:
        f = float(val)
        return None if (f != f) else f   # NaN check
    except (TypeError, ValueError):
        return fallback

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/stocks")
def get_all_stocks():
    """Return price + key metrics for all 25 NSE stocks in one batch call."""
    tickers = yf.Tickers(" ".join(NSE_STOCKS))
    results = []

    for symbol in NSE_STOCKS:
        try:
            t = tickers.tickers[symbol]
            info = t.info or {}

            price      = safe_val(info.get("currentPrice") or info.get("regularMarketPrice"))
            prev_close = safe_val(info.get("previousClose") or info.get("regularMarketPreviousClose"))
            change_pct = round((price - prev_close) / prev_close * 100, 2) if price and prev_close else None

            results.append({
                "symbol":        symbol.replace(".NS", ""),
                "name":          info.get("longName") or info.get("shortName") or symbol,
                "price":         price,
                "change_pct":    change_pct,
                "prev_close":    prev_close,
                "open":          safe_val(info.get("open") or info.get("regularMarketOpen")),
                "day_high":      safe_val(info.get("dayHigh") or info.get("regularMarketDayHigh")),
                "day_low":       safe_val(info.get("dayLow") or info.get("regularMarketDayLow")),
                "week_52_high":  safe_val(info.get("fiftyTwoWeekHigh")),
                "week_52_low":   safe_val(info.get("fiftyTwoWeekLow")),
                "volume":        safe_val(info.get("volume") or info.get("regularMarketVolume")),
                "market_cap":    safe_val(info.get("marketCap")),
                "pe_ratio":      safe_val(info.get("trailingPE")),
                "pb_ratio":      safe_val(info.get("priceToBook")),
                "div_yield":     safe_val(info.get("dividendYield")),
                "beta":          safe_val(info.get("beta")),
                "roe":           safe_val(info.get("returnOnEquity")),
                "debt_equity":   safe_val(info.get("debtToEquity")),
                "sector":        info.get("sector", "N/A"),
                "industry":      info.get("industry", "N/A"),
            })
        except Exception as e:
            results.append({
                "symbol": symbol.replace(".NS", ""),
                "error":  str(e)
            })

    return jsonify({"stocks": results})

@app.route("/stock/<symbol>")
def get_single_stock(symbol):
    """Detailed data for a single NSE stock (symbol without .NS)."""
    ticker_sym = symbol.upper() + ".NS"
    try:
        t = yf.Ticker(ticker_sym)
        info = t.info or {}
        hist = t.history(period="1mo")

        price      = safe_val(info.get("currentPrice") or info.get("regularMarketPrice"))
        prev_close = safe_val(info.get("previousClose") or info.get("regularMarketPreviousClose"))
        change_pct = round((price - prev_close) / prev_close * 100, 2) if price and prev_close else None

        history_data = []
        if not hist.empty:
            for date, row in hist.iterrows():
                history_data.append({
                    "date":   str(date.date()),
                    "open":   round(float(row["Open"]), 2),
                    "high":   round(float(row["High"]), 2),
                    "low":    round(float(row["Low"]), 2),
                    "close":  round(float(row["Close"]), 2),
                    "volume": int(row["Volume"])
                })

        return jsonify({
            "symbol":       symbol.upper(),
            "name":         info.get("longName") or info.get("shortName") or symbol,
            "price":        price,
            "change_pct":   change_pct,
            "prev_close":   prev_close,
            "open":         safe_val(info.get("open") or info.get("regularMarketOpen")),
            "day_high":     safe_val(info.get("dayHigh") or info.get("regularMarketDayHigh")),
            "day_low":      safe_val(info.get("dayLow") or info.get("regularMarketDayLow")),
            "week_52_high": safe_val(info.get("fiftyTwoWeekHigh")),
            "week_52_low":  safe_val(info.get("fiftyTwoWeekLow")),
            "volume":       safe_val(info.get("volume") or info.get("regularMarketVolume")),
            "market_cap":   safe_val(info.get("marketCap")),
            "pe_ratio":     safe_val(info.get("trailingPE")),
            "pb_ratio":     safe_val(info.get("priceToBook")),
            "div_yield":    safe_val(info.get("dividendYield")),
            "beta":         safe_val(info.get("beta")),
            "roe":          safe_val(info.get("returnOnEquity")),
            "debt_equity":  safe_val(info.get("debtToEquity")),
            "eps":          safe_val(info.get("trailingEps")),
            "sector":       info.get("sector", "N/A"),
            "industry":     info.get("industry", "N/A"),
            "description":  info.get("longBusinessSummary", ""),
            "history":      history_data
        })
    except Exception as e:
        return jsonify({"symbol": symbol.upper(), "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
