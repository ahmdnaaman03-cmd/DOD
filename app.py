import os, json, sqlite3, requests, stripe
from pusher import Pusher
from flask import Flask, request, jsonify, render_template, render_template_string
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

PUSHER_APP_ID = str(os.getenv("PUSHER_APP_ID") or "").strip()
PUSHER_KEY = str(os.getenv("PUSHER_KEY") or "").strip()
PUSHER_SECRET = str(os.getenv("PUSHER_SECRET") or "").strip()
PUSHER_CLUSTER = str(os.getenv("PUSHER_CLUSTER") or "eu").strip()

pusher_client = None
if PUSHER_APP_ID and PUSHER_KEY and PUSHER_SECRET:
    pusher_client = Pusher(
        app_id=PUSHER_APP_ID,
        key=PUSHER_KEY,
        secret=PUSHER_SECRET,
        cluster=PUSHER_CLUSTER,
        ssl=True
    )

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
SHOPIFY_STORE = os.getenv("SHOPIFY_STORE")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

DB_FILE = "paydod.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS orders (order_id TEXT PRIMARY KEY, status TEXT NOT NULL)')
    conn.commit()
    conn.close()

init_db()

def set_order_status(order_id, status):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT INTO orders (order_id, status) VALUES (?, ?) ON CONFLICT(order_id) DO UPDATE SET status=excluded.status', (order_id, status))
    conn.commit()
    conn.close()

def get_db_order_status(order_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT status FROM orders WHERE order_id = ?', (order_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else "PENDING"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/mandoob/<order_id>')
def mandoob_page(order_id):
    clean_id = order_id.replace('#', '').strip()
    current_status = get_db_order_status(clean_id)
    payment_url = f"https://Ahmdnoaman.pythonanywhere.com/pay/{clean_id}"
    qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={payment_url}&color=ffffff&bgcolor=0e1327"
    
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PayDOD - بوابة دفع المندوب</title>
        <script src="https://js.pusher.com/8.2.0/pusher.min.js"></script>
        <style>
            body {
                background-color: #060919;
                color: #ffffff;
                font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 20px;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                box-sizing: border-box;
            }
            .card {
                background: #0e1327;
                width: 100%;
                max-width: 380px;
                border-radius: 24px;
                padding: 35px 25px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
                text-align: center;
                border: 1px solid #1e293b;
            }
            .brand-logo {
                font-size: 34px;
                font-weight: 900;
                letter-spacing: -0.5px;
                margin-bottom: 8px;
            }
            .brand-logo .pay { color: #ffffff; }
            .brand-logo .d1 { color: #8b5cf6; }
            .brand-logo .o { color: #3b82f6; }
            .brand-logo .d2 { color: #06b6d4; }
            .order-badge {
                display: inline-block;
                background: rgba(255, 255, 255, 0.06);
                color: #94a3b8;
                padding: 6px 18px;
                border-radius: 20px;
                font-size: 14px;
                font-weight: 600;
                margin-bottom: 25px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            .qr-box {
                background: #0e1327;
                padding: 15px;
                border-radius: 20px;
                display: inline-block;
                border: 2px solid #8b5cf6;
                margin-bottom: 25px;
                box-shadow: 0 0 20px rgba(139, 92, 246, 0.2);
            }
            .qr-box img {
                display: block;
                width: 210px;
                height: 210px;
                border-radius: 10px;
            }
            .status-btn {
                padding: 16px;
                border-radius: 14px;
                font-size: 16px;
                font-weight: 700;
                transition: all 0.3s ease;
            }
            .pending {
                background: rgba(245, 158, 11, 0.15);
                color: #fbbf24;
                border: 1px solid rgba(245, 158, 11, 0.3);
            }
            .paid {
                background: rgba(16, 185, 129, 0.15);
                color: #34d399;
                border: 1px solid rgba(16, 185, 129, 0.4);
                box-shadow: 0 0 20px rgba(52, 211, 153, 0.2);
            }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="brand-logo">
                <span class="pay">Pay</span><span class="d1">D</span><span class="o">O</span><span class="d2">D</span>
            </div>
            
            <div class="order-badge">طلب رقم: #{{ order_id }}</div>
            
            <div id="qr-container">
                {% if status != 'PAID' %}
                    <p style="font-size:13px; color:#94a3b8; margin-bottom:15px;">امسح الـ QR للدفع الفوري</p>
                    <div class="qr-box">
                        <img src="{{ qr_url }}" alt="QR Code">
                    </div>
                {% endif %}
            </div>

            <div id="status" class="status-btn {% if status == 'PAID' %}paid{% else %}pending{% endif %}">
                {% if status == 'PAID' %}
                    ✅ تم الدفع بنجاح!
                {% else %}
                    ⏳ في انتظار تأكيد الدفع...
                {% endif %}
            </div>
        </div>

        <script>
        const pusher = new Pusher('{{ key }}', {cluster: '{{ cluster }}'});
        pusher.subscribe('order-{{ order_id }}').bind('payment-success', () => {
            const el = document.getElementById('status');
            el.innerText = '✅ تم الدفع بنجاح!';
            el.className = 'status-btn paid';
            const qrBox = document.getElementById('qr-container');
            if (qrBox) qrBox.style.display = 'none';
        });
        </script>
    </body>
    </html>
    ''', order_id=clean_id, status=current_status, qr_url=qr_code_url, key=PUSHER_KEY, cluster=PUSHER_CLUSTER)

@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    try:
        event = json.loads(payload)
        if event['type'] in ['checkout.session.completed', 'payment_intent.succeeded']:
            order_name = event['data']['object'].get('metadata', {}).get('order_name', '#1025')
            clean_id = order_name.replace('#', '').strip()
            set_order_status(clean_id, 'PAID')
            if pusher_client:
                pusher_client.trigger(f'order-{clean_id}', 'payment-success', {'status': 'PAID'})
    except Exception as e:
        print(f"Webhook error: {e}")
    return jsonify({'status': 'success'}), 200

if __name__ == '__main__':
    app.run(debug=True)
