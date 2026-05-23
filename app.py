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
def test():
    try:
        from nsepython import nse_eq
        data = nse_eq("RELIANCE")
        price = data["priceInfo"]["lastPrice"]
        change = data["priceInfo"]["change"]
        pct = data["priceInfo"]["pChange"]
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
