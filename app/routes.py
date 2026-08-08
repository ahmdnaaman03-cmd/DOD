from flask import Blueprint, jsonify, render_template, request
import qrcode
import io
import base64
import sqlite3

main = Blueprint('main', __name__)

@main.route('/')
def home():
    return render_template('index.html')

@main.route('/generate-qr/<order_id>/<float:amount>')
def generate_qr(order_id, amount):
    payment_data = f"PayDOD:ORDER_{order_id}:AMOUNT_{amount}"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(payment_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    
    qr_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    return jsonify({
        "order_id": order_id,
        "amount": amount,
        "qr_image_base64": qr_base64
    })

@main.route('/shopify-webhook', methods=['POST'])
def shopify_webhook():
    data = request.json
    if not data:
        return jsonify({"error": "No data received"}), 400
        
    order_id = data.get('id')
    financial_status = data.get('financial_status')
    
    conn = sqlite3.connect('paydod.db')
    c = conn.cursor()
    c.execute('''
        UPDATE shipments SET status = ? WHERE id = ?
    ''', (financial_status, str(order_id)))
    conn.commit()
    conn.close()
    
    return jsonify({"status": "success", "order_id": order_id, "updated_status": financial_status}), 200
