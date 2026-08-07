import os
import requests
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

API_VERSION = "2025-01" 
SHOPIFY_STORE = "aman-test-store-c9korns0.myshopify.com"
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")

HEADERS = {
    "X-Shopify-Access-Token": SHOPIFY_TOKEN,
    "Content-Type": "application/json"
}

@app.route('/')
def home():
    return render_template('driver.html')

@app.route('/api/get-shipment', methods=['GET'])
def get_shipment():
    order_name = request.args.get('id', '').strip()
    clean_name = order_name.replace('#', '')
    url = f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/orders.json?name=%23{clean_name}&status=any"
    try:
        res = requests.get(url, headers=HEADERS)
        if res.status_code == 200:
            orders = res.json().get('orders', [])
            if not orders:
                url2 = f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/orders.json?name={clean_name}&status=any"
                res = requests.get(url2, headers=HEADERS)
                orders = res.json().get('orders', [])
            if orders:
                order = orders[0]
                cust = order.get('customer', {})
                c_name = f"{cust.get('first_name', '')} {cust.get('last_name', '')}".strip() or "عميل"
                return jsonify({
                    "success": True, "shopify_order_id": order['id'],
                    "customer_name": c_name, "amount": order.get('total_price', 0)
                })
            return jsonify({"success": False, "message": "الطلب غير موجود"}), 404
        return jsonify({"success": False, "message": f"خطأ: {res.status_code}"}), res.status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/pay', methods=['POST'])
def pay_shipment():
    data = request.json or {}
    order_id = data.get('shopify_order_id')
    amount = data.get('amount')
    url = f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/orders/{order_id}/transactions.json"
    payload = {"transaction": {"kind": "capture", "status": "success", "amount": amount}}
    res = requests.post(url, json=payload, headers=HEADERS)
    if res.status_code in [200, 201]:
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "فشل الاتصال بـ شوبيفاي"}), 500

if __name__ == '__main__':
    app.run()
