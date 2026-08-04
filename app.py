import os
import requests
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

SHOPIFY_DOMAIN = os.environ.get("SHOPIFY_DOMAIN", "aman-test-store.myshopify.com")
SHOPIFY_ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN", "shpat_xxxxxxxxxxxxxxxxxxxxxxxx")

orders_db = {}

def update_shopify_paid(shopify_id, amount):
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2026-07/orders/{shopify_id}/transactions.json"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    payload = {
        "transaction": {
            "kind": "capture",
            "status": "success",
            "amount": str(amount)
        }
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        return res.status_code == 201
    except Exception as e:
        print("Shopify Error:", e)
        return False

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/shopify/webhook', methods=['POST'])
def shopify_webhook():
    data = request.get_json() or {}
    if 'id' in data:
        order_num = str(data.get('order_number') or data.get('name', '')).replace('#', '').strip()
        orders_db[order_num] = {
            "shopify_id": data.get('id'),
            "amount": data.get('total_price', '0.00')
        }
    return jsonify({"status": "ok"}), 200

@app.route('/api/get-order', methods=['POST'])
def get_order():
    data = request.get_json() or {}
    order_id = str(data.get('order_id', '')).replace('#', '').strip()
    
    if order_id in orders_db:
        return jsonify({"success": True, "amount": orders_db[order_id]["amount"]})
    return jsonify({"success": True, "amount": "949.95"})

@app.route('/api/confirm-payment', methods=['POST'])
def confirm_payment():
    data = request.get_json() or {}
    order_id = str(data.get('order_id', '')).replace('#', '').strip()
    amount = data.get('amount', '949.95')
    
    if order_id in orders_db:
        update_shopify_paid(orders_db[order_id]["shopify_id"], amount)
        
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True)
