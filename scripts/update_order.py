import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

SHOPIFY_STORE_URL = os.getenv("SHOPIFY_STORE_URL")
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
API_VERSION = "2024-01"

headers = {
    "X-Shopify-Access-Token": ACCESS_TOKEN,
    "Content-Type": "application/json"
}

def get_order_graphql_id(order_name):
    clean_name = order_name.replace("#", "").strip()
    graphql_url = f"https://{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}/graphql.json"
    
    query = """
    query ($query: String!) {
      orders(first: 1, query: $query) {
        edges {
          node {
            id
            name
          }
        }
      }
    }
    """
    variables = {"query": f"name:#{clean_name}"}
    
    res = requests.post(graphql_url, json={'query': query, 'variables': variables}, headers=headers)
    if res.status_code == 200:
        data = res.json()
        edges = data.get('data', {}).get('orders', {}).get('edges', [])
        if edges:
            return edges[0]['node']['id']
    return None

def mark_order_as_paid_graphql(order_name):
    order_id = get_order_graphql_id(order_name)
    if not order_id:
        print(f"Error: Order {order_name} not found!")
        return

    graphql_url = f"https://{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}/graphql.json"
    
    mutation = """
    mutation orderMarkAsPaid($input: OrderMarkAsPaidInput!) {
      orderMarkAsPaid(input: $input) {
        order {
          id
          fullyPaid
          displayFinancialStatus
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    variables = {
        "input": {
            "id": order_id
        }
    }
    
    res = requests.post(graphql_url, json={'query': mutation, 'variables': variables}, headers=headers)
    if res.status_code == 200:
        result = res.json()
        errors = result.get('data', {}).get('orderMarkAsPaid', {}).get('userErrors', [])
        if not errors:
            print(f"Success: Order {order_name} is now PAID via GraphQL!")
        else:
            print(f"Failed: {errors[0]['message']}")
    else:
        print(f"HTTP Error: {res.text}")

if __name__ == "__main__":
    target_order = input("Enter Order Number (e.g. #1008): ")
    mark_order_as_paid_graphql(target_order)
