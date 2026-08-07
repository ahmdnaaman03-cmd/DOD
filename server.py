import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__, static_folder='.', static_url_path='')

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE_URL", "aman-test-store.myshopify.com")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "shpat_xxxxxxxxxxxxxxxxxxxxxxxx")

HEADERS = {
    "X-Shopify-Access-Token": SHOPIFY_TOKEN,
    "Content-Type": "application/json"
}

@app.route('/')
def home():
    return app.send_static_file('driver.html')

@app.route('/pay')
def pay_page():
    return app.send_static_file('pay.html')

@app.route('/api/get-shipment', methods=['GET'])
def get_shipment():
    order_name = request.args.get('id')
    if not order_name:
        return jsonify({"success": False, "message": "رقم الطلب مطلوب"}), 400
    
    formatted_name = f"#{order_name}" if not order_name.startswith("#") else order_name
    url = f"https://{SHOPIFY_STORE}/admin/api/2024-01/orders.json?name={formatted_name}&status=any"
    
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            orders = res.json().get('orders', [])
            if orders:
                order = orders[0]
                cust = order.get('customer', {})
                c_name = f"{cust.get('first_name', '')} {cust.get('last_name', '')}".strip() or "عميل متجر"
                total = float(order.get('total_price', 0.0))
                status = order.get('financial_status', 'pending')
                return jsonify({
                    "success": True,
                    "shopify_order_id": order['id'],
                    "order_number": order_name,
                    "customer_name": c_name,
                    "amount": total,
                    "status": "PAID" if status == "paid" else "PENDING"
                })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
        
    return jsonify({"success": False, "message": "الطلب غير موجود في Shopify"}), 404

@app.route('/api/pay', methods=['POST'])
def pay_shipment():
    data = request.json or {}
    order_id = data.get('shopify_order_id')
    amount = data.get('amount')

    if not order_id:
        return jsonify({"success": False, "message": "بيانات غير مكتملة"}), 400

    url = f"https://{SHOPIFY_STORE}/admin/api/2024-01/orders/{order_id}/transactions.json"
    payload = {"transaction": {"kind": "capture", "status": "success", "amount": amount}}
    
    try:
        res = requests.post(url, json=payload, headers=HEADERS, timeout=10)
        if res.status_code in [200, 201]:
            return jsonify({"success": True, "message": "تم التحديث لـ Paid بنجاح!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    return jsonify({"success": False, "message": "فشل التحديث في Shopify"}), 500

if __name__ == '__main__':
    app.run(debug=True)
