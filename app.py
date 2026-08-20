import os
import sqlite3
import requests
import stripe
from flask import Flask, request, jsonify, render_template, redirect
from pusher import Pusher

app = Flask(__name__)

# --- Configurations ---
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "sk_test_YOUR_STRIPE_SECRET")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_YOUR_WEBHOOK_SECRET")
SHOPIFY_STORE_URL = os.getenv("SHOPIFY_STORE_URL", "your-store.myshopify.com")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "shpat_YOUR_SHOPIFY_TOKEN")

PUSHER_APP_ID = os.getenv("PUSHER_APP_ID", "YOUR_APP_ID")
PUSHER_KEY = os.getenv("PUSHER_KEY", "YOUR_KEY")
PUSHER_SECRET = os.getenv("PUSHER_SECRET", "YOUR_SECRET")
PUSHER_CLUSTER = os.getenv("PUSHER_CLUSTER", "mt1")

stripe.api_key = STRIPE_SECRET_KEY

pusher_client = Pusher(
    app_id=PUSHER_APP_ID,
    key=PUSHER_KEY,
    secret=PUSHER_SECRET,
    cluster=PUSHER_CLUSTER,
    ssl=True
)

def get_db():
    conn = sqlite3.connect('paydod.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shopify_order_id TEXT UNIQUE,
                amount REAL,
                currency TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.commit()

init_db()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    data = request.get_json() or {}
    shopify_order_id = data.get('shopify_order_id')
    amount = int(float(data.get('amount', 10.0)) * 100)

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'egp',
                    'product_data': {
                        'name': f'PayDOD Order #{shopify_order_id}',
                    },
                    'unit_amount': amount,
                },
                'quantity': 1,
            }],
            mode='payment',
            metadata={'shopify_order_id': shopify_order_id},
            success_url=request.host_url + 'success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.host_url + 'cancel',
        )

        with get_db() as db:
            db.execute(
                'INSERT OR REPLACE INTO orders (shopify_order_id, amount, status) VALUES (?, ?, ?)',
                (shopify_order_id, amount / 100, 'PENDING')
            )
            db.commit()

        return jsonify({'id': session.id, 'url': session.url})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    try:
        if STRIPE_WEBHOOK_SECRET != "whsec_YOUR_WEBHOOK_SECRET":
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        else:
            event = request.get_json()
    except Exception as e:
        return jsonify({'status': 'invalid payload', 'error': str(e)}), 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        shopify_order_id = session.get('metadata', {}).get('shopify_order_id')

        if shopify_order_id:
            with get_db() as db:
                db.execute(
                    'UPDATE orders SET status = ? WHERE shopify_order_id = ?',
                    ('PAID', shopify_order_id)
                )
                db.commit()

            update_shopify_order(shopify_order_id)

            pusher_client.trigger('paydod-channel', 'payment-success', {
                'shopify_order_id': shopify_order_id,
                'status': 'PAID',
                'message': 'تم الدفع بنجاح!'
            })

    return jsonify({'status': 'success'}), 200

def update_shopify_order(shopify_order_id):
    url = f"https://{SHOPIFY_STORE_URL}/admin/api/2024-01/orders/{shopify_order_id}/transactions.json"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    data = {
        "transaction": {
            "kind": "capture",
            "status": "success",
            "amount": "10.00"
        }
    }
    try:
        requests.post(url, json=data, headers=headers, timeout=10)
    except Exception as e:
        print(f"Shopify Sync Error: {e}")

@app.route('/success')
def success():
    return "<h1>تمت عملية الدفع بنجاح! يتم الآن تحديث شاشة المندوب وشوبيفاي...</h1>"

if __name__ == '__main__':
    app.run(debug=True)
