import os
import requests
from flask import Flask, jsonify, request
from dotenv import load_dotenv

# تحميل المتغيرات من ملف .env
load_dotenv()

app = Flask(__name__)

SHOPIFY_STORE_URL = os.getenv("SHOPIFY_STORE_URL")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

headers = {
    "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
    "Content-Type": "application/json"
}

@app.route('/')
def home():
    return jsonify({"status": "PayDoD API is running", "store": SHOPIFY_STORE_URL})

@app.route('/get-order/<order_name>', methods=['GET'])
def get_order(order_name):
    url = f"https://{SHOPIFY_STORE_URL}/admin/api/2024-01/orders.json?name={order_name}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        orders = response.json().get('orders', [])
        if orders:
            order = orders[0]
            return jsonify({
                "success": True,
                "shopify_order_id": order['id'],
                "order_name": order['name'],
                "total_price": order['total_price'],
                "financial_status": order['financial_status']
            })
    return jsonify({"success": False, "message": "الطلب غير موجود"}), 404

@app.route('/mark-as-paid', methods=['POST'])
def mark_as_paid():
    data = request.json or {}
    shopify_order_id = data.get('shopify_order_id')
    amount = data.get('amount')
    
    url = f"https://{SHOPIFY_STORE_URL}/admin/api/2024-01/orders/{shopify_order_id}/transactions.json"
    payload = {
        "transaction": {
            "kind": "capture",
            "status": "success",
            "amount": str(amount)
        }
    }
    
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code in [200, 201]:
        return jsonify({"success": True, "message": "تم تحديث حالة الدفع إلى Paid بنجاح!"})
    
    return jsonify({"success": False, "error": response.json()}), 400

if __name__ == '__main__':
    app.run(debug=True)
