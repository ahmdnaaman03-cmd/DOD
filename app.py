import os
import json
import requests
import stripe
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
SHOPIFY_GRAPHQL_URL = f"https://{SHOPIFY_STORE}.myshopify.com/admin/api/2024-07/graphql.json" if SHOPIFY_STORE else None

orders_db = {}

def get_shopify_order_gid(order_name):
    if not SHOPIFY_GRAPHQL_URL or not SHOPIFY_ACCESS_TOKEN:
        return None
    headers = {"Content-Type": "application/json", "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN}
    query = """
    query getOrderDetails($query: String!) {
      orders(first: 1, query: $query) {
        edges { node { id } }
      }
    }
    """
    variables = {"query": f"name:{order_name}"}
    try:
        res = requests.post(SHOPIFY_GRAPHQL_URL, json={'query': query, 'variables': variables}, headers=headers)
        edges = res.json().get("data", {}).get("orders", {}).get("edges", [])
        if edges:
            return edges[0]["node"]["id"]
    except Exception as e:
        print(f"Error fetching GID: {e}")
    return None

def mark_shopify_order_as_paid(order_gid):
    if not SHOPIFY_GRAPHQL_URL or not SHOPIFY_ACCESS_TOKEN or not order_gid:
        return False
    headers = {"Content-Type": "application/json", "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN}
    mutation = """
    mutation markOrderAsPaid($input: OrderMarkAsPaidInput!) {
      orderMarkAsPaid(input: $input) {
        order { id displayFinancialStatus }
        userErrors { field message }
      }
    }
    """
    variables = {"input": {"id": order_gid}}
    try:
        res = requests.post(SHOPIFY_GRAPHQL_URL, json={'query': mutation, 'variables': variables}, headers=headers)
        errors = res.json().get("data", {}).get("orderMarkAsPaid", {}).get("userErrors", [])
        return len(errors) == 0
    except Exception as e:
        print(f"Error marking order paid: {e}")
        return False

@app.route('/api/order-status/<order_id>', methods=['GET'])
def get_order_status(order_id):
    clean_id = order_id.replace("#", "")
    status = orders_db.get(clean_id, "PENDING")
    return jsonify({"order_id": clean_id, "status": status})

@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')

    try:
        if STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        else:
            event = json.loads(payload)
    except Exception as e:
        print(f"Webhook Signature Error: {e}")
        return jsonify({'status': 'invalid payload'}), 400

    if event['type'] in ['checkout.session.completed', 'payment_intent.succeeded']:
        session = event['data']['object']
        metadata = session.get('metadata', {})
        order_name = metadata.get('order_name', '#1025')
        clean_order_id = order_name.replace("#", "")

        # 1. تحديث لشاشة المندوب
        orders_db[clean_order_id] = "PAID"
        print(f"[Mandoob DB] Order #{clean_order_id} set to PAID")

        # 2. تحديث Shopify
        gid = get_shopify_order_gid(order_name)
        if gid:
            success = mark_shopify_order_as_paid(gid)
            print(f"[Shopify GraphQL] Order {order_name} paid status: {success}")

    return jsonify({'status': 'success'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
