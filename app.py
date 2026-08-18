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

SHOPIFY_STORE_URL = os.getenv('SHOPIFY_SHOP_URL')
ACCESS_TOKEN = os.getenv('SHOPIFY_ACCESS_TOKEN')
API_VERSION = "2024-01"

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
            print(f"Processing paid order via GraphQL: {order_number}", file=sys.stderr)
            update_shopify_order(order_number, session.get('amount_total', 0) / 100)

    return '', 200

def update_shopify_order(order_number, amount):
    if not SHOPIFY_STORE_URL or not ACCESS_TOKEN:
        print("Shopify credentials missing!", file=sys.stderr)
        return

    clean_name = str(order_number).replace("#", "").strip()
    graphql_url = f"https://{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}/graphql.json"
    
    headers = {
        "X-Shopify-Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    
    # 1. البحث في الطلبات العادية (Orders)
    query_order = """
    query ($query: String!) {
      orders(first: 1, query: $query) {
        edges { node { id name } }
      }
    }
    """
    vars_order = {"query": f"name:#{clean_name} OR name:{clean_name}"}
    res_order = requests.post(graphql_url, json={'query': query_order, 'variables': vars_order}, headers=headers)
    
    order_id = None
    if res_order.status_code == 200:
        edges = res_order.json().get('data', {}).get('orders', {}).get('edges', [])
        if edges:
            order_id = edges[0]['node']['id']

    # إذا وجدناه كـ Order عادي، نقوم بتحديثه بالمارك أس بيد
    if order_id:
        mutation_order = """
        mutation orderMarkAsPaid($input: OrderMarkAsPaidInput!) {
          orderMarkAsPaid(input: $input) {
            order { id fullyPaid }
            userErrors { message }
          }
        }
        """
        mut_res = requests.post(graphql_url, json={'query': mutation_order, 'variables': {"input": {"id": order_id}}}, headers=headers)
        print(f"Shopify Order Update Result: {mut_res.status_code} - {mut_res.text}", file=sys.stderr)
        return

    # 2. إذا لم نجد order، نبحث في مسودات الطلبات (Draft Orders)
    query_draft = """
    query ($query: String!) {
      draftOrders(first: 1, query: $query) {
        edges { node { id name status } }
      }
    }
    """
    vars_draft = {"query": f"name:#{clean_name} OR name:{clean_name}"}
    res_draft = requests.post(graphql_url, json={'query': query_draft, 'variables': vars_draft}, headers=headers)
    
    draft_id = None
    if res_draft.status_code == 200:
        edges_draft = res_draft.json().get('data', {}).get('draftOrders', {}).get('edges', [])
        if edges_draft:
            draft_id = edges_draft[0]['node']['id']

    # إذا وجدناه كـ Draft Order، نقوم بتأكيده وتحويله لـ Paid
    if draft_id:
        mutation_draft = """
        mutation draftOrderComplete($id: ID!) {
          draftOrderComplete(id: $id, paymentPending: false) {
            draftOrder { id status }
            userErrors { message }
          }
        }
        """
        mut_draft_res = requests.post(graphql_url, json={'query': mutation_draft, 'variables': {"id": draft_id}}, headers=headers)
        print(f"Shopify Draft Order Complete Result: {mut_draft_res.status_code} - {mut_draft_res.text}", file=sys.stderr)
        return

    print(f"Order or Draft Order {order_number} not found in Shopify.", file=sys.stderr)

if __name__ == '__main__':
    app.run(debug=True)
