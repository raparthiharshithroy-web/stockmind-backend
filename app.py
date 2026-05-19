from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return jsonify({"status": "ok"})

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/test')
def test_jugaad():
    try:
        from jugaad_data.nse import NSELive
        n = NSELive()
        q = n.stock_quote("RELIANCE")
        price = q["priceInfo"]["lastPrice"]
        change = q["priceInfo"]["change"]
        pct = q["priceInfo"]["pChange"]
        return jsonify({
            "success": True,
            "symbol": "RELIANCE",
            "price": price,
            "change": change,
            "changePercent": pct
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
