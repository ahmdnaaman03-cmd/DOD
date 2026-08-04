import os
import sqlite3
import requests
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect('dod.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            amount REAL,
            status TEXT DEFAULT 'AWAITING_PAYMENT'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

PAYMOB_API_KEY = os.getenv("PAYMOB_API_KEY", "YOUR_PAYMOB_API_KEY")
PAYMOB_INTEGRATION_ID = os.getenv("PAYMOB_INTEGRATION_ID", "YOUR_INTEGRATION_ID")

def get_paymob_token():
    url = "https://accept.paymob.com/api/auth/tokens"
    res = requests.post(url, json={"api_key": PAYMOB_API_KEY})
    return res.json().get("token")

@app.route("/api/generate-qr", methods=["POST"])
def generate_qr():
    data = request.get_json() or {}
    order_id = str(data.get("order_id", ""))
    amount = float(data.get("amount", 100.0))  # افتراضي أو يتم جلبه من Shopify
    
    conn = sqlite3.connect('dod.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO orders (order_id, amount, status) VALUES (?, ?, 'AWAITING_PAYMENT')", (order_id, amount))
    conn.commit()
    conn.close()
    
    # هنا يتم توليد رابط الدفع والـ QR Code من Paymob
    qr_url = f"https://accept.paymob.com/api/acceptance/iframes/YOUR_IFRAME_ID?order_id={order_id}"
    return jsonify({"status": "success", "order_id": order_id, "qr_url": qr_url})

@app.route("/webhook/paymob", methods=["POST"])
def paymob_webhook():
    data = request.get_json() or {}
    obj = data.get("obj", {})
    success = obj.get("success", False)
    order_id = str(obj.get("order", {}).get("merchant_order_id", ""))
    
    if success and order_id:
        conn = sqlite3.connect('dod.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE orders SET status = 'PAID' WHERE order_id = ?", (order_id,))
        conn.commit()
        conn.close()
        # هنا يمكن إضافة إشعار لـ Shopify لتحديث الحالة إلى Paid
        return jsonify({"status": "updated_to_paid"}), 200
    return jsonify({"status": "ignored"}), 200

@app.route("/api/check-status/<order_id>", methods=["GET"])
def check_status(order_id):
    conn = sqlite3.connect('dod.db')
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM orders WHERE order_id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    
    status = row[0] if row else "NOT_FOUND"
    return jsonify({"order_id": order_id, "status": status})

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>D.O.D - Digital-on-Delivery</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { background: #000; color: #fff; font-family: sans-serif; text-align: center; padding: 20px; }
        input { padding: 15px; font-size: 18px; width: 80%; margin-bottom: 20px; text-align: center; border-radius: 8px; }
        button { padding: 15px 30px; font-size: 18px; background: #e63946; color: #fff; border: none; border-radius: 25px; cursor: pointer; }
        .status { margin-top: 30px; font-size: 22px; color: #4e4; }
    </style>
</head>
<body>
    <h1>D.O.D</h1>
    <div id="app">
        <input type="text" id="order_id" placeholder="ENTER ORDER #">
        <br>
        <button onclick="generateQR()">GENERATE</button>
        <div id="result" class="status"></div>
    </div>
    <script>
        let pollTimer = null;
        function generateQR() {
            let id = document.getElementById('order_id').value;
            if(!id) return alert('Enter Order ID');
            document.getElementById('result').innerHTML = "AWAITING PAYMENT...";
            
            fetch('/api/generate-qr', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({order_id: id, amount: 150.0})
            });

            if(pollTimer) clearInterval(pollTimer);
            pollTimer = setInterval(() => {
                fetch('/api/check-status/' + id)
                .then(res => res.json())
                .then(data => {
                    if(data.status === 'PAID') {
                        document.getElementById('result').innerHTML = "PAYMENT SUCCESSFUL ✔";
                        clearInterval(pollTimer);
                    }
                });
            }, 2000);
        }
    </script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def home():
    return render_template_string(HTML_TEMPLATE)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
