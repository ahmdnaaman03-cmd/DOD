import os
import json
import stripe
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Stripe API Key
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/support')
def support():
    return render_template('support.html')

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        data = request.get_json() or {}
        order_id = str(data.get('shopify_order_id', '')).replace('#', '').strip()
        amount_egp = float(data.get('amount', 0))

        if not order_id or amount_egp <= 0:
            return jsonify({'error': 'رقم الطلب أو المبلغ غير صحيح'}), 400

        unit_amount = int(amount_egp * 100)
        domain = request.host_url.rstrip('/')

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'egp',
                    'product_data': {
                        'name': f'Shopify Order #{order_id}',
                    },
                    'unit_amount': unit_amount,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f'{domain}/?success=true',
            cancel_url=f'{domain}/?canceled=true',
            metadata={'order_name': f'#{order_id}'}
        )

        return jsonify({'checkout_url': session.url})

    except Exception as e:
        print(f"Stripe Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    try:
        event = json.loads(request.get_data(as_text=True))
        if event.get('type') in ['checkout.session.completed', 'payment_intent.succeeded']:
            print("Payment Received Successfully!")
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)
