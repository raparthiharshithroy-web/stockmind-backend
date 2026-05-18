from flask import Flask, jsonify
from flask_cors import CORS
import yfinance as yf
import traceback

app = Flask(__name__)
CORS(app)

SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", "ITC.NS",
    "BAJFINANCE.NS", "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "TITAN.NS", "WIPRO.NS", "HCLTECH.NS", "NTPC.NS",
    "ONGC.NS", "POWERGRID.NS", "ADANIENT.NS", "ADANIPORTS.NS", "JSWSTEEL.NS"
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
        ticker = yf.Ticker(symbol)

        # Get last 5 days of data for current price + previous close
        recent = ticker.history(period="5d")
        if recent.empty:
            return jsonify({"error": f"No data for {symbol}"}), 404

        current_price = recent['Close'].iloc[-1]
        prev_close = recent['Close'].iloc[-2] if len(recent) > 1 else current_price
        day_high = recent['High'].iloc[-1]
        day_low = recent['Low'].iloc[-1]
        volume = recent['Volume'].iloc[-1]

        change = current_price - prev_close
        change_pct = (change / prev_close) * 100 if prev_close else 0

        # Get 1 month of history for chart
        hist = ticker.history(period="1mo")
        chart_data = [
            {"date": str(d.date()), "close": round(row['Close'], 2)}
            for d, row in hist.iterrows()
        ] if not hist.empty else []

        data = {
            "symbol": symbol,
            "name": symbol.replace(".NS", ""),  # Use symbol as name for now
            "currentPrice": round(current_price, 2),
            "previousClose": round(prev_close, 2),
            "change": round(change, 2),
            "changePercent": round(change_pct, 2),
            "dayHigh": round(day_high, 2) if day_high else None,
            "dayLow": round(day_low, 2) if day_low else None,
            "volume": int(volume) if volume else None,
            "marketCap": None,
            "pe": None,
            "sector": "N/A",
            "history": chart_data
        }
        return jsonify(data)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
