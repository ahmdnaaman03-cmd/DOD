from flask import Flask, render_template, request, jsonify
import sqlite3
import os

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('dod_orders.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            amount REAL,
            status TEXT
        )
    ''')
    cursor.execute("INSERT OR REPLACE INTO orders VALUES ('9082', 245.00, 'PENDING')")
    cursor.execute("INSERT OR REPLACE INTO orders VALUES ('1001', 500.00, 'PENDING')")
    conn.commit()
    conn.close()

@app.route('/')
def courier_view():
    return render_template('index.html')

@app.route('/api/order/<order_id>')
def get_order(order_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT order_id, amount, status FROM orders WHERE order_id = ?', (order_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return jsonify({"order_id": row[0], "amount": row[1], "status": row[2]})
    return jsonify({"order_id": order_id, "amount": 250.00, "status": "PENDING"})

@app.route('/payment-webhook', methods=['POST'])
def webhook():
    data = request.json or {}
    order_id = data.get('order_id')
    status = data.get('status')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO orders (order_id, amount, status) VALUES (?, 245.00, ?)', (order_id, status))
    conn.commit()
    conn.close()
    return jsonify({"message": "Status updated successfully", "status": status}), 200

@app.route('/api/simulate-payment/<order_id>', methods=['POST'])
def simulate_payment(order_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO orders (order_id, amount, status) VALUES (?, 245.00, "PAID")', (order_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Payment Simulated", "status": "PAID"}), 200

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
