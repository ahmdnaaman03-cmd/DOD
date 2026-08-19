import os, json, sqlite3, requests, stripe
from pusher import Pusher
from flask import Flask, request, jsonify, render_template_string
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
PUSHER_APP_ID = str(os.getenv("PUSHER_APP_ID") or "").strip()
PUSHER_KEY = str(os.getenv("PUSHER_KEY") or "").strip()
PUSHER_SECRET = str(os.getenv("PUSHER_SECRET") or "").strip()
PUSHER_CLUSTER = str(os.getenv("PUSHER_CLUSTER") or "eu").strip()

pusher_client = None
if PUSHER_APP_ID and PUSHER_KEY and PUSHER_SECRET:
    pusher_client = Pusher(app_id=PUSHER_APP_ID, key=PUSHER_KEY, secret=PUSHER_SECRET, cluster=PUSHER_CLUSTER, ssl=True)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
DB_FILE = "paydod.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute('CREATE TABLE IF NOT EXISTS orders (order_id TEXT PRIMARY KEY, status TEXT NOT NULL)')
    conn.commit(); conn.close()
init_db()

def set_order_status(order_id, status):
    conn = sqlite3.connect(DB_FILE)
    conn.execute('INSERT INTO orders (order_id, status) VALUES (?, ?) ON CONFLICT(order_id) DO UPDATE SET status=excluded.status', (order_id, status))
    conn.commit(); conn.close()
def get_db_order_status(order_id):
    conn = sqlite3.connect(DB_FILE)
    row = conn.execute('SELECT status FROM orders WHERE order_id = ?', (order_id,)).fetchone()
    conn.close()
    return row[0] if row else "PENDING"

@app.route('/')
def home():
    return render_template_string('''<!DOCTYPE html>
    <html lang="ar" dir="rtl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PayDOD Checkout</title>
    <style>body { background: #060919; color: #fff; font-family: sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }
    .card { background: #0e1327; width: 100%; max-width: 400px; border-radius: 24px; padding: 35px 25px; box-shadow: 0 20px 40px rgba(0,0,0,0.6); text-align: center; border: 1px solid #1e293b; }
    .brand { font-size: 36px; font-weight: 900; margin-bottom: 6px; } .brand .pay { color: #fff; } .brand .d1 { color: #8b5cf6; } .brand .o { color: #3b82f6; } .brand .d2 { color: #06b6d4; }
    .subtitle { color: #94a3b8; font-size: 13px; margin-bottom: 25px; line-height: 1.5; }
    .input-group { text-align: right; margin-bottom: 20px; } label { font-size: 13px; color: #cbd5e1; display: block; margin-bottom: 8px; font-weight: 600; }
    input { width: 100%; padding: 14px; border-radius: 12px; border: 1px solid #334155; background: #1e293b; color: #fff; font-size: 15px; box-sizing: border-box; outline: none; }
    .btn { background: linear-gradient(135deg, #8b5cf6, #3b82f6); color: #fff; border: none; width: 100%; padding: 16px; border-radius: 12px; font-size: 16px; font-weight: 700; cursor: pointer; }</style></head>
    <body><div class="card"><div class="brand"><span class="pay">Pay</span><span class="d1">D</span><span class="o">O</span><span class="d2">D</span></div>
    <div class="subtitle">توليد دفع رقمي فوري لطلبات شوبيفاي<br><span style="color:#64748b;">Instant Digital Payment for Shopify Orders</span></div>
    <form action="#" onsubmit="event.preventDefault(); window.location.href='/mandoob/' + document.getElementById('order').value.replace('#','');">
    <div class="input-group"><label>رقم الطلب / Order ID</label><input type="text" id="order" placeholder="e.g. 1025" required></div>
    <button type="submit" class="btn">توليد الـ QR Code والرابط</button></form></div></body></html>''')
@app.route('/mandoob/<order_id>')
def mandoob_page(order_id):
    clean_id = order_id.replace('#', '').strip()
    st = get_db_order_status(clean_id)
    url = f"https://Ahmdnoaman.pythonanywhere.com/pay/{clean_id}"
    qr = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={url}&color=ffffff&bgcolor=0e1327"
    return render_template_string('''<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PayDOD - بوابة دفع المندوب</title><script src="https://js.pusher.com/8.2.0/pusher.min.js"></script>
    <style>body { background-color: #060919; color: #fff; font-family: sans-serif; margin: 0; padding: 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; box-sizing: border-box; }
    .card { background: #0e1327; width: 100%; max-width: 380px; border-radius: 24px; padding: 35px 25px; text-align: center; border: 1px solid #1e293b; }
    .brand-logo { font-size: 36px; font-weight: 900; margin-bottom: 6px; } .pay { color: #fff; } .d1 { color: #8b5cf6; } .o { color: #3b82f6; } .d2 { color: #06b6d4; }
    .order-badge { display: inline-block; background: rgba(255,255,255,0.06); color: #94a3b8; padding: 6px 18px; border-radius: 20px; font-size: 14px; font-weight: 600; margin-bottom: 25px; }
    .qr-box { background: #0e1327; padding: 15px; border-radius: 20px; display: inline-block; border: 2px solid #8b5cf6; margin-bottom: 25px; } .qr-box img { width: 210px; height: 210px; border-radius: 10px; }
    .status-btn { padding: 16px; border-radius: 14px; font-size: 15px; font-weight: 700; transition: all 0.3s ease; }
    .pending { background: rgba(245,158,11,0.15); color: #fbbf24; border: 1px solid rgba(245,158,11,0.3); }
    .paid { background: rgba(16,185,129,0.15); color: #34d399; border: 1px solid rgba(16,185,129,0.4); } .sub-text { font-size: 11px; display: block; margin-top: 4px; opacity: 0.8; }</style></head>
    <body><div class="card"><div class="brand-logo"><span class="pay">Pay</span><span class="d1">D</span><span class="o">O</span><span class="d2">D</span></div>
    <div class="order-badge">طلب رقم / Order: #{{ oid }}</div>
    <div id="qr-container">{% if st != 'PAID' %}<p style="font-size:13px; color:#94a3b8; margin-bottom:15px;">امسح الـ QR للدفع الفوري<span class="sub-text">Scan QR Code to Pay</span></p>
    <div class="qr-box"><img src="{{ qr }}" alt="QR Code"></div>{% endif %}</div>
    <div id="status" class="status-btn {% if st == 'PAID' %}paid{% else %}pending{% endif %}">
    {% if st == 'PAID' %}✅ تم الدفع بنجاح!<span class="sub-text">Paid Successfully</span>
    {% else %}⏳ في انتظار تأكيد الدفع...<span class="sub-text">Awaiting Payment Confirm</span>{% endif %}</div></div>
    <script>
    const pusher = new Pusher('{{ key }}', {cluster: '{{ cluster }}'});
    pusher.subscribe('order-{{ oid }}').bind('payment-success', () => {
        const el = document.getElementById('status');
        el.innerHTML = '✅ تم الدفع بنجاح!<span class="sub-text">Paid Successfully</span>';
        el.className = 'status-btn paid';
        const qrBox = document.getElementById('qr-container');
        if (qrBox) qrBox.style.display = 'none';
    });</script></body></html>''', oid=clean_id, st=st, qr=qr, key=PUSHER_KEY, cluster=PUSHER_CLUSTER)

@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    try:
        event = json.loads(request.get_data(as_text=True))
        if event['type'] in ['checkout.session.completed', 'payment_intent.succeeded']:
            clean_id = event['data']['object'].get('metadata', {}).get('order_name', '#1025').replace('#', '').strip()
            set_order_status(clean_id, 'PAID')
            if pusher_client: pusher_client.trigger(f'order-{clean_id}', 'payment-success', {'status': 'PAID'})
    except Exception as e: print(f"Webhook error: {e}")
    return jsonify({'status': 'success'}), 200

if __name__ == '__main__':
    app.run(debug=True)

@app.route('/pay/<order_id>')
def pay_page(order_id):
    clean_id = order_id.replace('#', '').strip()
    try:
        if stripe.api_key:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'egp',
                        'product_data': {'name': f'طلب شوبيفاي #{clean_id}'},
                        'unit_amount': 15000,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f'https://Ahmdnoaman.pythonanywhere.com/mandoob/{clean_id}',
                cancel_url=f'https://Ahmdnoaman.pythonanywhere.com/mandoob/{clean_id}',
                metadata={'order_name': f'#{clean_id}'}
            )
            return f'<script>window.location.href="{session.url}";</script>'
    except Exception as e:
        print(f"Stripe Error: {e}")
    
    return f"<h3>صفحة الدفع التجريبية للطلب #{clean_id}</h3><p>رابط الدفع يعمل بنجاح!</p>"
