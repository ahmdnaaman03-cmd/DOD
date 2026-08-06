from flask import Flask, render_template, jsonify
import sqlite3

app = Flask(__name__)

@app.route('/')
def index():
    conn = sqlite3.connect('database/dod_orders.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders;")
    orders = cursor.fetchall()
    conn.close()
    return render_template('index.html', orders=orders)

@app.route('/api/orders')
def api_orders():
    conn = sqlite3.connect('database/dod_orders.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders;")
    orders = cursor.fetchall()
    conn.close()
    return jsonify({"orders": orders})

if __name__ == '__main__':
    app.run(debug=True)
