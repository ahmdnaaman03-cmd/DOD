import os, json, sqlite3, requests, stripe
from pusher import Pusher
from flask import Flask, request, jsonify, render_template, render_template_string
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# --- إعدادات آمنة من .env ---
pusher_client = Pusher(
  app_id=os.getenv("PUSHER_APP_ID"),
  key=os.getenv("PUSHER_KEY"),
  secret=os.getenv("PUSHER_SECRET"),
  cluster=os.getenv("PUSHER_CLUSTER"),
  ssl=True
)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
SHOPIFY_STORE = os.getenv("SHOPIFY_STORE")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
SHOPIFY_GRAPHQL_URL = f"https://{SHOPIFY_STORE}.myshopify.com/admin/api/2024-01/graphql.json" if SHOPIFY_STORE else None

DB_FILE = "paydod.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS orders (order_id TEXT PRIMARY KEY, status TEXT NOT NULL)')
    conn.commit(); conn.close()

init_db()

def set_order_status(order_id, status):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT INTO orders (order_id, status) VALUES (?, ?) ON CONFLICT(order_id) DO UPDATE SET status=excluded.status', (order_id, status))
    conn.commit(); conn.close()

def get_db_order_status(order_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT status FROM orders WHERE order_id = ?', (order_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else "PENDING"

# --- 1. الصفحة الرئيسية (تفتح index.html) ---
@app.route('/')
def home():
    return render_template('index.html')

# --- 2. شاشة المندوب ---
@app.route('/mandoob/<order_id>')
def mandoob_page(order_id):
    clean_id = order_id.replace('#', '').strip()
    current_status = get_db_order_status(clean_id)
    return render_template_string('''
    <!DOCTYPE html><html lang="ar" dir="rtl">
    <head><meta charset="UTF-8"><title>PayDOD - شاشة المندوب</title><script src="https://js.pusher.com/8.2.0/pusher.min.js"></script></head>
    <body style="text-align:center; padding:50px; font-family:sans-serif;">
        <h2>طلب رقم: #{{ order_id }}</h2>
        <div id="status" style="font-size:24px; font-weight:bold; padding:20px; border-radius:10px; background: {% if status == 'PAID' %}#d4edda{% else %}#fff3cd{% endif %};">
            {% if status == 'PAID' %}✅ تم الدفع بنجاح!{% else %}⏳ في انتظار تأكيد الدفع...{% endif %}
        </div>
        <script>
        const pusher = new Pusher('{{ key }}', {cluster: '{{ cluster }}'});
        pusher.subscribe('order-{{ order_id }}').bind('payment-success', () => {
            const el = document.getElementById('status');
            el.innerText = '✅ تم الدفع بنجاح!';
            el.style.background = '#d4edda';
        });
        </script>
    </body></html>''', order_id=clean_id, status=current_status, key=os.getenv("PUSHER_KEY"), cluster=os.getenv("PUSHER_CLUSTER"))

# --- 3. Webhook استقبال الدفع ---
@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    try:
        event = json.loads(payload)
        if event['type'] in ['checkout.session.completed', 'payment_intent.succeeded']:
            order_name = event['data']['object'].get('metadata', {}).get('order_name', '#1025')
            clean_id = order_name.replace('#', '').strip()
            set_order_status(clean_id, 'PAID')
            pusher_client.trigger(f'order-{clean_id}', 'payment-success', {'status': 'PAID'})
    except Exception as e:
        print(f"Webhook error: {e}")
    return jsonify({'status': 'success'}), 200

if __name__ == '__main__':
    app.run(debug=True)
