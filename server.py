import requests
from flask import Flask, request, jsonify, render_template
from config import API_VERSION, SHOPIFY_STORE, HEADERS
from utils import create_qr_code

app = Flask(__name__)

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
            if orders:
                order = orders[0]
                cust = order.get('customer', {})
                c_name = f"{cust.get('first_name', '')} {cust.get('last_name', '')}".strip() or "عميل"
                return jsonify({"success": True, "shopify_order_id": order['id'], "customer_name": c_name, "amount": order.get('total_price', 0)})
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
    return jsonify({"success": False, "message": f"فشل الاتصال ({res.status_code})"}), res.status_code

@app.route('/api/generate_qr', methods=['POST'])
def generate_qr():
    data = request.json or {}
    if not data or 'amount' not in data or 'shopify_order_id' not in data:
        return jsonify({"success": False, "error": "Missing fields"}), 400

    amount, order_id = data.get('amount'), data.get('shopify_order_id')
    if amount is None or order_id is None:
        return jsonify({"success": False, "error": "None values"}), 400

    qr_image = create_qr_code(order_id, amount)
    if not qr_image:
        return jsonify({"success": False, "error": "QR failed"}), 500

    return jsonify({"success": True, "qr_data": qr_image}), 200

if __name__ == '__main__':
    app.run()
