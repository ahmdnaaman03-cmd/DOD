import os
import sys
import stripe
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'paydod-secret-key')

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

SHOPY_URL = os.getenv('SHOPIFY_SHOP_URL')
SHOPIFY_TOKEN = os.getenv('SHOPIFY_ACCESS_TOKEN')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_payment():
    order_id = request.form.get('order_id')
    amount = request.form.get('amount')

    if not order_id or not amount:
        return jsonify({'error': 'Missing Order ID or Amount'}), 400

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': f'PayDOD Order: {order_id}'},
                    'unit_amount': int(float(amount) * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            metadata={'order_number': order_id},
            success_url=request.host_url + 'success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.host_url,
        )
        return jsonify({'url': session.url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/success')
def success():
    return "<h2 style='text-align:center; color:green; margin-top:50px;'>Payment Successful! Order Confirmed via PayDOD.</h2>"

@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    event = None

    try:
        if STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        else:
            event = request.get_json()
    except Exception as e:
        print(f"Webhook signature verification failed: {e}", file=sys.stderr)
        return jsonify({'error': str(e)}), 400

    if event.get('type') in ['checkout.session.completed', 'payment_intent.succeeded']:
        session = event.get('data', {}).get('object', {})
        metadata = session.get('metadata', {})
        order_number = metadata.get('order_number')

        if order_number:
            print(f"Processing paid order: {order_number}", file=sys.stderr)
            update_shopify_order(order_number, session.get('amount_total', 0) / 100)

    return '', 200

def update_shopify_order(order_number, amount):
    if not SHOPY_URL or not SHOPIFY_TOKEN:
        print("Shopify credentials missing!", file=sys.stderr)
        return

    clean_order_num = order_number.replace('#', '')
    search_url = f"https://{SHOPY_URL}/admin/api/2024-01/orders.json?name=%23{clean_order_num}&status=any"
    headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}

    res = requests.get(search_url, headers=headers)
    orders = res.json().get('orders', [])

    if not orders:
        print(f"Shopify order {order_number} not found via API search.", file=sys.stderr)
        return

    shopify_order_id = orders[0]['id']

    txn_url = f"https://{SHOPY_URL}/admin/api/2024-01/orders/{shopify_order_id}/transactions.json"
    txn_data = {
        "transaction": {
            "currency": "USD",
            "amount": str(amount),
            "kind": "sale",
            "status": "success"
        }
    }
    txn_res = requests.post(txn_url, json=txn_data, headers=headers)
    print(f"Shopify update result for {order_number}: {txn_res.status_code}", file=sys.stderr)

if __name__ == '__main__':
    app.run(debug=True)
