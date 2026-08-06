from flask import Flask, request, jsonify, render_template_string
import sqlite3

app = Flask(__name__)

# Initialize database
def init_db():
    conn = sqlite3.connect('paydod.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS shipments (order_id TEXT PRIMARY KEY, customer_name TEXT, amount REAL, status TEXT)')
    c.execute("INSERT OR IGNORE INTO shipments VALUES ('1001', 'John Doe', 350.0, 'Pending')")
    conn.commit()
    conn.close()

init_db()

# Lightweight professional mobile UI in English with brand colors (Dark Navy, Purple, Cyan)
UI = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PayDOD - Driver Portal</title>
    <style>
        body { background-color: #0A0F1D; color: #FFF; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: #131B2E; padding: 24px; border-radius: 16px; width: 320px; border: 1px solid rgba(0,191,255,0.2); }
        h1 { text-align: center; font-size: 24px; margin-bottom: 20px; }
        span.pay { color: #FFF; }
        span.dod { background: linear-gradient(90deg, #8A2BE2, #00BFFF); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        input { width: 100%; padding: 12px; background: #0A0F1D; border: 1px solid #2A3B5C; color: #FFF; border-radius: 8px; margin-bottom: 12px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background: linear-gradient(90deg, #8A2BE2, #00BFFF); border: none; color: #FFF; font-weight: bold; border-radius: 8px; cursor: pointer; }
        .result { margin-top: 15px; font-size: 14px; display: none; background: #0A0F1D; padding: 10px; border-radius: 6px; }
    </style>
</head>
<body>
    <div class="card">
        <h1><span class="pay">Pay</span><span class="dod">DOD</span></h1>
        <input type="text" id="orderId" placeholder="Enter Order ID (e.g. 1001)">
        <button onclick="fetchOrder()">Get QR & Details</button>
        <div id="res" class="result">
            <p>Customer: <span id="cName"></span></p>
            <p>Amount: <span id="cAmount" style="color: #00BFFF;"></span></p>
            <p><a id="cLink" href="#" target="_blank" style="color: #00BFFF;">Open Payment Link</a></p>
        </div>
    </div>
    <script>
        async function fetchOrder() {
            let id = document.getElementById('orderId').value;
            let res = await fetch('/api/get', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({order_id: id}) });
            let data = await res.json();
            if(data.status === 'success') {
                document.getElementById('cName').innerText = data.customer_name;
                document.getElementById('cAmount').innerText = '$' + data.amount;
                document.getElementById('cLink').href = data.payment_link;
                document.getElementById('res').style.display = 'block';
            } else {
                alert('Order not found');
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(UI)

@app.route('/api/get', methods=['POST'])
def get_order():
    data = request.json
    conn = sqlite3.connect('paydod.db')
    c = conn.cursor()
    c.execute("SELECT customer_name, amount, status FROM shipments WHERE order_id = ?", (data.get('order_id'),))
    row = c.fetchone()
    conn.close()
    if row:
        return jsonify({"status": "success", "customer_name": row[0], "amount": row[1], "payment_link": f"https://paydod.com/pay?id={data.get('order_id')}&amt={row[1]}"})
    return jsonify({"status": "error"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
