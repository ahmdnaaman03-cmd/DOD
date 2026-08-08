from flask import Flask, request, jsonify
import qrcode
import io
import base64

app = Flask(__name__)

def create_qr_code(order_id, amount):
    try:
        payload = f"PayDOD:Order-{order_id}:Amount-{amount}"
        img = qrcode.make(payload)
        
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        return img_str
    except Exception as e:
        print(f"Error generating QR: {e}")
        return None

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    data = request.get_json()
    
    # حماية من البيانات الفارغة لمنع خطأ NoneType
    if not data or 'amount' not in data or 'order_id' not in data:
        return jsonify({"error": "Missing required fields"}), 400

    amount = data.get('amount')
    order_id = data.get('order_id')

    if amount is None or order_id is None:
        return jsonify({"error": "Values cannot be None"}), 400

    qr_image = create_qr_code(order_id, amount)
    
    if qr_image is None:
        return jsonify({"error": "Failed to generate QR code image"}), 500

    return jsonify({"status": "success", "qr_data": qr_image}), 200

if __name__ == '__main__':
    app.run(debug=True)
