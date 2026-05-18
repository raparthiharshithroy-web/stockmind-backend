from flask import Flask, jsonify
from flask_cors import CORS
import yfinance as yf
import traceback

app = Flask(__name__)
CORS(app)

# Top 25 NSE stocks
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
        info = ticker.info
        hist = ticker.history(period="1mo")
        if hist.empty:
            return jsonify({"error": f"No data for {symbol}"}), 404

        current_price = info.get('currentPrice') or info.get('regularMarketPrice') or hist['Close'].iloc[-1]
        prev_close = info.get('previousClose') or (hist['Close'].iloc[-2] if len(hist) > 1 else current_price)
        change = current_price - prev_close
        change_pct = (change / prev_close) * 100 if prev_close else 0

        data = {
            "symbol": symbol,
            "name": info.get('shortName') or info.get('longName') or symbol,
            "currentPrice": round(current_price, 2),
            "previousClose": round(prev_close, 2),
            "change": round(change, 2),
            "changePercent": round(change_pct, 2),
            "dayHigh": info.get('dayHigh'),
            "dayLow": info.get('dayLow'),
            "volume": info.get('volume'),
            "marketCap": info.get('marketCap'),
            "pe": info.get('trailingPE'),
            "sector": info.get('sector'),
            "history": [
                {"date": str(d.date()), "close": round(row['Close'], 2)}
                for d, row in hist.iterrows()
            ]
        }
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
