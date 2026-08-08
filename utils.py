import qrcode
import io
import base64

def create_qr_code(order_id, amount):
    try:
        payload = f"PayDOD:Order-{order_id}:Amount-{amount}"
        img = qrcode.make(payload)
        
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"Error generating QR: {e}")
        return None
