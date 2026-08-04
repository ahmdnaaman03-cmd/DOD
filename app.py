import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify, g
import qrcode
import io
import base64

app = Flask(__name__)
DATABASE = os.path.join(os.path.dirname(__file__), 'dod_orders.db')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                amount REAL NOT NULL,
                status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.commit()

init_db()
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>D.O.D. - Digital on Delivery</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        :root { --bg-color: #0d1117; --card-bg: #161b22; --border-color: #30363d; --accent-blue: #2f81f7; --accent-green: #238636; --accent-red: #da3633; --text-main: #f0f6fc; --text-muted: #8b949e; }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Tajawal', sans-serif; }
        body { background-color: var(--bg-color); color: var(--text-main); display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 15px; }
        .container { width: 100%; max-width: 400px; background-color: var(--card-bg); border: 1px solid var(--border-color); border-radius: 20px; padding: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); text-align: center; }
        .logo-title { font-size: 26px; font-weight: 900; color: var(--accent-blue); margin-bottom: 4px; }
        .subtitle { font-size: 13px; color: var(--text-muted); margin-bottom: 20px; }
        .input-group { margin-bottom: 16px; text-align: right; }
        label { display: block; font-size: 13px; color: var(--text-muted); margin-bottom: 6px; font-weight: 700; }
        input { width: 100%; padding: 12px 14px; background-color: var(--bg-color); border: 1px solid var(--border-color); border-radius: 10px; color: var(--text-main); font-size: 16px; outline: none; text-align: center; }
        button { width: 100%; padding: 13px; background-color: var(--accent-blue); color: #ffffff; border: none; border-radius: 10px; font-size: 15px; font-weight: 700; cursor: pointer; transition: 0.2s; }
        button:active { transform: scale(0.98); }
        .btn-next { background-color: var(--accent-green) !important; margin-top: 15px; display: none; }
        .qr-section { display: none; margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--border-color); }
        .amount-tag { font-size: 22px; font-weight: 900; color: #ffffff; margin-bottom: 12px; }
        .qr-box { background-color: #ffffff; padding: 12px; border-radius: 14px; display: inline-block; margin-bottom: 12px; }
        .qr-box img { width: 180px; height: 180px; display: block; }
        .status-badge { display: inline-block; padding: 8px 14px; border-radius: 20px; font-size: 13px; font-weight: 700; background-color: rgba(238, 169, 13, 0.15); color: #f1e05a; border: 1px solid rgba(238, 169, 13, 0.3); }
        .status-badge.success { background-color: rgba(35, 134, 54, 0.15); color: #3fb950; border-color: rgba(35, 134, 54, 0.3); }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo-title">.D.O.D</div>
        <div class="subtitle">Digital-on-Delivery Payment</div>

        <div class="input-group">
            <label for="orderId">رقم الطلب (Order ID)</label>
            <input type="text" id="orderId" placeholder="أدخل رقم الطلب..." autocomplete="off">
        </div>

        <button id="genBtn" onclick="fetchOrderAndGenerateQR()">توليد كود الدفع (QR Code)</button>

        <div id="qrSection" class="qr-section">
            <div id="amountDisplay" class="amount-tag"></div>
            
            <div class="qr-box">
                <img id="qrImage" src="" alt="QR Code">
            </div>

            <div>
                <span id="statusBadge" class="status-badge">في انتظار دفع العميل...</span>
            </div>

            <button id="nextBtn" class="btn-next" onclick="resetForNextOrder()">طلب جديد (Next Order)</button>
        </div>
    </div>

    <script>
        function fetchOrderAndGenerateQR() {
            const orderId = document.getElementById('orderId').value.trim();
            if (!orderId) { alert('برجاء إدخال رقم الطلب أولاً'); return; }

            fetch('/generate_qr', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ order_id: orderId })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('amountDisplay').innerText = `المبلغ المطلوب: ${data.amount} ج.م`;
                    document.getElementById('qrImage').src = data.qr_code;
                    document.getElementById('qrSection').style.display = 'block';
                    document.getElementById('genBtn').style.display = 'none';

                    if (data.status === 'PAID') {
                        const badge = document.getElementById('statusBadge');
                        badge.innerText = '✓ تم الدفع سابقاً (ALREADY PAID)';
                        badge.classList.add('success');
                        document.getElementById('nextBtn').style.display = 'block';
                    } else {
                        setTimeout(() => {
                            const badge = document.getElementById('statusBadge');
                            badge.innerText = '✓ تم الدفع بنجاح (PAYMENT SUCCESSFUL)';
                            badge.classList.add('success');
                            document.getElementById('nextBtn').style.display = 'block';
                        }, 5000);
                    }
                } else { alert(data.message || 'حدث خطأ أثناء توليد الكود'); }
            });
        }

        function resetForNextOrder() {
            document.getElementById('orderId').value = '';
            document.getElementById('qrSection').style.display = 'none';
            document.getElementById('genBtn').style.display = 'block';
            const badge = document.getElementById('statusBadge');
            badge.innerText = 'في انتظار دفع العميل...';
            badge.classList.remove('success');
            document.getElementById('orderId').focus();
        }
    </script>
</body>
</html>
"""
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    data = request.get_json() or {}
    order_id = str(data.get('order_id', '')).strip()

    if not order_id:
        return jsonify({'success': False, 'message': 'رقم الطلب مطلوب'}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM orders WHERE order_id = ?', (order_id,))
    order = cursor.fetchone()

    if order:
        amount = order['amount']
        status = order['status']
    else:
        amount = 250.0
        status = 'PENDING'

    pay_url = f"https://Ahmdnoaman.pythonanywhere.com/pay/{order_id}"

    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(pay_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode('utf-8')

    return jsonify({
        'success': True,
        'order_id': order_id,
        'amount': amount,
        'status': status,
        'qr_code': qr_b64
    })

@app.route('/pay/<order_id>')
def pay_page(order_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM orders WHERE order_id = ?', (order_id,))
    order = cursor.fetchone()

    if order and order['status'] == 'PAID':
        return f"""
        <div style="text-align:center; padding:50px; font-family:sans-serif;">
            <h1 style="color:#da3633;">⚠️ تم الدفع مسبقاً</h1>
            <p>الطلب رقم <b>#{order_id}</b> تم سداده بالفعل سابقاً. لا يمكن تكرار عملية الدفع.</p>
        </div>
        """

    amount = order['amount'] if order else 250.0
    return f"""
    <div style="text-align:center; padding:50px; font-family:sans-serif;">
        <h1 style="color:#2f81f7;">.D.O.D Payment Gate</h1>
        <p>دفع الطلب رقم: <b>#{order_id}</b></p>
        <h2>المبلغ المطلوب: {amount} ج.م</h2>
        <p style="color:#238636;">[ محاكاة بوابة الدفع Paymob / Stripe ]</p>
    </div>
    """

@app.route('/api/shopify/webhook', methods=['POST'])
def shopify_webhook():
    try:
        data = request.get_json(force=True)
        order_id = str(data.get('order_number') or data.get('id', ''))
        total_price = float(data.get('total_price', 0.0))

        if order_id:
            db = get_db()
            cursor = db.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO orders (order_id, amount, status)
                VALUES (?, ?, 'PENDING')
            ''', (order_id, total_price))
            db.commit()

        return jsonify({'status': 'success'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)
