import os
import requests
from flask import Flask, jsonify, request, render_template_string
from dotenv import load_dotenv

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

@app.route('/driver')
def driver_screen():
    html_content = '''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>شاشة المندوب - D.O.D</title>
        <style>
            body { font-family: Tahoma, sans-serif; background: #121212; color: #fff; margin: 0; padding: 20px; text-align: center; }
            .card { background: #1e1e1e; padding: 20px; border-radius: 10px; max-width: 400px; margin: 20px auto; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
            input { width: 80%; padding: 10px; margin: 10px 0; border-radius: 5px; border: 1px solid #444; background: #2a2a2a; color: #fff; font-size: 16px; text-align: center; }
            button { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-size: 16px; width: 85%; }
            button:hover { background: #0056b3; }
            .status { margin-top: 15px; font-weight: bold; font-size: 18px; }
            .paid { color: #28a745; }
            .pending { color: #ffc107; }
        </style>
    </head>
    <body>
        <h2>D.O.D - شاشة المندوب</h2>
        <div class="card">
            <input type="text" id="orderInput" placeholder="أدخل رقم الطلب (مثال: #1001)">
            <br>
            <button onclick="checkOrder()">فحص الطلب</button>
            <div id="result" class="status"></div>
        </div>

        <script>
        let currentOrderName = "";

        function fetchOrderStatus() {
            if (!currentOrderName) return;
            fetch('/get-order/' + currentOrderName)
                .then(res => res.json())
                .then(data => {
                    let resDiv = document.getElementById('result');
                    if (data.success) {
                        let statusText = data.financial_status === 'paid' ? 'تم الدفع بنجاح (Paid)' : 'في انتظار الدفع (Pending)';
                        let statusClass = data.financial_status === 'paid' ? 'paid' : 'pending';
                        resDiv.innerHTML = `رقم الطلب: ${data.order_name}<br>المبلغ: ${data.total_price} ج.م<br><span class="${statusClass}">${statusText}</span>`;
                    }
                });
        }

        function checkOrder() {
            currentOrderName = document.getElementById('orderInput').value.trim();
            if (currentOrderName) {
                fetchOrderStatus();
            }
        }

        setInterval(fetchOrderStatus, 2000);
        </script>
    </body>
    </html>
    '''
    return render_template_string(html_content)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
