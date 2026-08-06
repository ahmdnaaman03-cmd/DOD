from flask import Flask, request, jsonify, render_template
import sqlite3

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('paydod.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS shipments 
                 (order_id TEXT PRIMARY KEY, customer_name TEXT, amount REAL, status TEXT, shopify_order_id TEXT)''')
    c.execute("INSERT OR REPLACE INTO shipments VALUES ('1001', 'John Doe', 350.0, 'PENDING', '55443322')")
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('driver.html')

@app.route('/pay')
def pay():
    order_id = request.args.get('id')
    conn = sqlite3.connect('paydod.db')
    c = conn.cursor()
    c.execute("SELECT customer_name, amount FROM shipments WHERE order_id = ?", (order_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return render_template('pay.html', order_id=order_id, customer_name=row[0], amount=row[1])
    return "Order Not Found", 404
@app.route('/api/get', methods=['POST'])
def get_order():
    data = request.json
    conn = sqlite3.connect('paydod.db')
    c = conn.cursor()
    c.execute("SELECT customer_name, amount, status FROM shipments WHERE order_id = ?", (data.get('order_id'),))
    row = c.fetchone()
    conn.close()
    if row:
        pay_url = f"{request.host_url}pay?id={data.get('order_id')}"
        return jsonify({"status": "success", "customer_name": row[0], "amount": row[1], "payment_link": pay_url})
    return jsonify({"status": "error"}), 404

@app.route('/api/check_status')
def check_status():
    order_id = request.args.get('order_id')
    conn = sqlite3.connect('paydod.db')
    c = conn.cursor()
    c.execute("SELECT status FROM shipments WHERE order_id = ?", (order_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return jsonify({"status": row[0]})
    return jsonify({"status": "NOT_FOUND"}), 404

@app.route('/webhook/payment', methods=['POST'])
def payment_webhook():
    data = request.json
    order_id = data.get('order_id')
    status = data.get('status')
    
    if status == 'PAID':
        conn = sqlite3.connect('paydod.db')
        c = conn.cursor()
        c.execute("UPDATE shipments SET status = 'PAID' WHERE order_id = ?", (order_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Order status updated to PAID"}), 200
    return jsonify({"status": "ignored"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
