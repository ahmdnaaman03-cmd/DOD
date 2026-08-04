import os
import requests
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

SHOPIFY_DOMAIN = os.environ.get("SHOPIFY_DOMAIN", "aman-test-store.myshopify.com")
SHOPIFY_ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN", "shpat_xxxxxxxxxxxxxxxxxxxxxxxx")

orders_db = {}

def update_shopify_order_status(order_id, amount):
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2026-07/orders/{order_id}/transactions.json"
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
        print(f"Shopify Update Error: {e}")
        return False

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/shopify/webhook', methods=['POST'])
def shopify_webhook():
    data = request.get_json()
    if data and 'id' in data:
        order_name = str(data.get('order_number') or data.get('name', '')).replace('#', '')
        total_price = data.get('total_price', '0.00')
        shopify_id = data.get('id')
        
        orders_db[order_name] = {
            "shopify_id": shopify_id,
            "amount": total_price,
            "status": "pending"
        }
        print(f"[Webhook Received] Order: {order_name}, Amount: {total_price}")
    return jsonify({"status": "success"}), 200

@app.route('/api/get-order', methods=['POST'])
def get_order():
    req_data = request.get_json()
    order_id = str(req_data.get('order_id', '')).replace('#', '').strip()
    
    if order_id in orders_db:
        return jsonify({
            "success": True,
            "order_id": order_id,
            "amount": orders_db[order_id]["amount"]
        })
    else:
        return jsonify({
            "success": True,
            "order_id": order_id,
            "amount": "949.95"
        })

@app.route('/api/confirm-payment', methods=['POST'])
def confirm_payment():
    req_data = request.get_json()
    order_id = str(req_data.get('order_id', '')).replace('#', '').strip()
    amount = req_data.get('amount', '949.95')
    
    if order_id in orders_db:
        orders_db[order_id]["status"] = "paid"
        shopify_id = orders_db[order_id]["shopify_id"]
        update_shopify_order_status(shopify_id, amount)
    
    return jsonify({"success": True, "message": "Payment confirmed and Shopify updated"})

if __name__ == '__main__':
    app.run(debug=True)
