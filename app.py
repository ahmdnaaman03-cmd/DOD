import os, json, sqlite3, stripe
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
    <html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PayDOD - Instant Payment QR Codes</title>
    <style>
        body { background: #0b0f19; color: #fff; font-family: sans-serif; margin: 0; padding: 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; box-sizing: border-box; }
        .card { background: #111827; width: 100%; max-width: 420px; border-radius: 20px; padding: 30px 24px; border: 1px solid #1f2937; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); text-align: center; }
        .brand { font-size: 28px; font-weight: 800; color: #fff; margin-bottom: 20px; } .brand span { color: #818cf8; }
        .hero-title { font-size: 22px; font-weight: 700; line-height: 1.3; color: #f3f4f6; margin-bottom: 10px; }
        .hero-sub { font-size: 13px; color: #9ca3af; margin-bottom: 25px; line-height: 1.5; }
        .input-box { text-align: left; margin-bottom: 16px; }
        .input-box label { font-size: 12px; color: #d1d5db; display: block; margin-bottom: 6px; font-weight: 600; }
        .input-box input { width: 100%; padding: 14px; border-radius: 10px; border: 1px solid #374151; background: #1f2937; color: #fff; font-size: 15px; box-sizing: border-box; outline: none; }
        .btn { background: #6366f1; color: #fff; border: none; width: 100%; padding: 15px; border-radius: 10px; font-size: 15px; font-weight: 600; cursor: pointer; }
    </style></head>
    <body><div class="card"><div class="brand">Pay<span>DOD</span></div>
    <div class="hero-title">Instant Payment QR Codes for Your Business</div>
    <div class="hero-sub">Generate seamless Stripe checkout links and QR codes instantly without setting up a full store.</div>
    <form action="#" onsubmit="event.preventDefault(); const o=document.getElementById('oid').value.replace('#',''); const a=document.getElementById('amt').value; window.location.href='/mandoob/' + o + '?amount=' + a;">
    <div class="input-box"><label>Order ID</label><input type="text" id="oid" placeholder="e.g. ORD-9901" required></div>
    <div class="input-box"><label>Amount ($)</label><input type="number" step="any" id="amt" placeholder="e.g. 49.00" required></div>
    <button type="submit" class="btn">Generate Payment QR</button></form></div></body></html>''')

@app.route('/mandoob/<order_id>')
def mandoob_page(order_id):
    clean_id = order_id.replace('#', '').strip()
    amount = request.args.get('amount', '100')
    st = get_db_order_status(clean_id)
    pay_link = f"https://Ahmdnoaman.pythonanywhere.com/pay/{clean_id}?amount={amount}"
    qr = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={pay_link}&color=ffffff&bgcolor=111827"
    return render_template_string('''<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PayDOD - Checkout</title><script src="https://js.pusher.com/8.2.0/pusher.min.js"></script>
    <style>
        body { background: #0b0f19; color: #fff; font-family: sans-serif; margin: 0; padding: 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; box-sizing: border-box; }
        .card { background: #111827; width: 100%; max-width: 420px; border-radius: 20px; padding: 30px 24px; border: 1px solid #1f2937; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); text-align: center; }
        .brand { font-size: 28px; font-weight: 800; color: #fff; margin-bottom: 15px; } .brand span { color: #818cf8; }
        .order-info { background: #1f2937; padding: 12px; border-radius: 10px; font-size: 14px; color: #9ca3af; margin-bottom: 20px; }
        .qr-box { background: #111827; padding: 10px; border-radius: 14px; display: inline-block; border: 1px solid #374151; margin-bottom: 15px; } .qr-box img { width: 210px; height: 210px; border-radius: 8px; }
        .pay-url { display: inline-block; color: #818cf8; font-size: 14px; font-weight: 600; margin-bottom: 20px; text-decoration: none; }
        .status-btn { padding: 14px; border-radius: 10px; font-size: 14px; font-weight: 700; }
        .pending { background: rgba(245,158,11,0.1); color: #fbbf24; border: 1px solid rgba(245,158,11,0.2); }
        .paid { background: rgba(16,185,129,0.1); color: #34d399; border: 1px solid rgba(16,185,129,0.2); }
    </style></head>
    <body><div class="card"><div class="brand">Pay<span>DOD</span></div>
    <div class="order-info">Order <strong>#{{ oid }}</strong> • Amount: <strong>${{ amount }}</strong></div>
    <div id="qr-container">{% if st != 'PAID' %}
    <div style="font-size:13px; color:#9ca3af; margin-bottom:10px;">Scan to Pay:</div>
    <div class="qr-box"><img src="{{ qr }}" alt="QR Code"></div><br>
    <a href="{{ pay_link }}" target="_blank" class="pay-url">Or click here to pay directly →</a>{% endif %}</div>
    <div id="status" class="status-btn {% if st == 'PAID' %}paid{% else %}pending{% endif %}">
    {% if st == 'PAID' %}✅ Paid Successfully{% else %}⏳ Awaiting Payment...{% endif %}</div></div>
    <script>
    const pusher = new Pusher('{{ key }}', {cluster: '{{ cluster }}'});
    pusher.subscribe('order-{{ oid }}').bind('payment-success', () => {
        const el = document.getElementById('status');
        el.innerHTML = '✅ Paid Successfully';
        el.className = 'status-btn paid';
        const qrBox = document.getElementById('qr-container');
        if (qrBox) qrBox.style.display = 'none';
    });</script></body></html>''', oid=clean_id, amount=amount, st=st, qr=qr, pay_link=pay_link, key=PUSHER_KEY, cluster=PUSHER_CLUSTER)

@app.route('/pay/<order_id>')
def pay_route(order_id):
    clean_id = order_id.replace('#', '').strip()
    amount = float(request.args.get('amount', '100'))
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': f'Order #{clean_id}'},
                    'unit_amount': int(amount * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f'https://Ahmdnoaman.pythonanywhere.com/mandoob/{clean_id}?amount={amount}',
            cancel_url=f'https://Ahmdnoaman.pythonanywhere.com/mandoob/{clean_id}?amount={amount}',
            metadata={'order_name': f'#{clean_id}'}
        )
        return f'<script>window.location.href="{session.url}";</script>'
    except Exception as e:
        return f"<h3>Stripe Error:</h3><p>{e}</p>"

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
