from flask import Flask, request, jsonify
import sqlite3
import pusher
import os
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

pusher_client = pusher.Pusher(
    app_id=os.getenv('PUSHER_APP_ID'),
    key=os.getenv('PUSHER_KEY'),
    secret=os.getenv('PUSHER_SECRET'),
    cluster=os.getenv('PUSHER_CLUSTER'),
    ssl=True
)

SHOPIFY_SHOP_URL = os.getenv('SHOPIFY_SHOP_URL') 
SHOPIFY_ACCESS_TOKEN = os.getenv('SHOPIFY_ACCESS_TOKEN')

def init_db():
    conn = sqlite3.connect('paydod.db')
    c = conn.cursor()
    c.execute('DROP TABLE IF EXISTS orders')
    c.execute('''CREATE TABLE orders
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, status TEXT, order_id TEXT)''')
    conn.commit()
    conn.close()

def update_shopify_order(order_id):
    if not SHOPIFY_SHOP_URL or not SHOPIFY_ACCESS_TOKEN:
        return False
    
    url = f"https://{SHOPIFY_SHOP_URL}/admin/api/2024-01/orders/{order_id}.json"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    payload = {
        "order": {
            "id": order_id,
            "financial_status": "paid"
        }
    }
    response = requests.put(url, json=payload, headers=headers)
    return response.status_code == 200

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    order_id = data.get('order_id') or data.get('id')
    
    if order_id:
        update_shopify_order(order_id)
        
        pusher_client.trigger('paydod-channel', 'payment-event', {
            'message': '✅ تم الدفع بنجاح',
            'order_id': order_id
        })
        
        return jsonify({"status": "success", "message": "Shopify and Courier updated"}), 200
        
    return jsonify({"status": "error", "message": "Invalid data"}), 400

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
