import os
from dotenv import load_dotenv

load_dotenv()

API_VERSION = "2025-01"
SHOPIFY_STORE = os.getenv("SHOPIFY_STORE_URL", "aman-test-store-c9korns0.myshopify.com")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")

HEADERS = {
    "X-Shopify-Access-Token": SHOPIFY_TOKEN,
    "Content-Type": "application/json"
}
