from flask import Blueprint, jsonify
import qrcode
import io
import base64

main = Blueprint('main', __name__)

@main.route('/')
def home():
    return jsonify({
        "status": "PayDOD System Active",
        "model": "B2B SaaS",
        "version": "2.0"
    })

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
