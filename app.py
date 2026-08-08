from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

@app.route('/generate-qr', methods=['POST'])
def generate_qr():
    data = request.get_json(silent=True)
    if not data:
        data = request.form
        
    order_id = data.get('order_id') if data else None
    
    if not order_id:
        return jsonify({'error': 'رقم الطلب غير موجود أو البيانات فارغة'}), 400
        
    # منطق توليد الـ QR ومعالجة الطلب
    return jsonify({'success': True, 'order_id': order_id}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
