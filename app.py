import os
import json
import stripe
import requests
import pusher
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify

load_dotenv()
app = Flask(__name__)

stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

try:
    pusher_client = pusher.Pusher(
      app_id=os.environ.get('PUSHER_APP_ID', ''),
      key=os.environ.get('PUSHER_KEY', ''),
      secret=os.environ.get('PUSHER_SECRET', ''),
      cluster=os.environ.get('PUSHER_CLUSTER', ''),
      ssl=True
    )
except:
    pusher_client = None

@app.route('/')
def home():
    return render_template('index.html')

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
                    'product_data': {'name': f'Shopify Order #{order_id}'},
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
        return jsonify({'error': str(e)}), 500

@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    try:
        event = json.loads(request.get_data(as_text=True))
        
        if event.get('type') == 'checkout.session.completed':
            session_data = event.get('data', {}).get('object', {})
            order_name = session_data.get('metadata', {}).get('order_name', '').replace('#', '')

            shop_url = os.environ.get('SHOPIFY_SHOP_URL')
            token = os.environ.get('SHOPIFY_ACCESS_TOKEN')
            
            if shop_url and token and order_name:
                headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
                query = """
                query getOrder($query: String!) {
                  orders(first: 1, query: $query) { edges { node { id } } }
                }
                """
                res = requests.post(f"https://{shop_url}/admin/api/2024-01/graphql.json", 
                                    json={"query": query, "variables": {"query": f"name:#{order_name}"}}, 
                                    headers=headers).json()
                
                edges = res.get('data', {}).get('orders', {}).get('edges', [])
                if edges:
                    graphql_order_id = edges[0]['node']['id']
                    mutation = """
                    mutation addTags($id: ID!, $tags: [String!]!) {
                      tagsAdd(id: $id, tags: $tags) { node { id } }
                    }
                    """
                    requests.post(f"https://{shop_url}/admin/api/2024-01/graphql.json", 
                                  json={"query": mutation, "variables": {"id": graphql_order_id, "tags": ["Paid_via_PayDOD"]}}, 
                                  headers=headers)

            if pusher_client:
                try:
                    pusher_client.trigger('paydod-channel', 'payment-success', {'order_id': order_name})
                except Exception as e:
                    print("Pusher Error:", e)

        return jsonify({'status': 'success'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)
