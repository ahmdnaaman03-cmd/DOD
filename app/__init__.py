from flask import Flask
from .models import init_db

def create_app():
    app = Flask(__name__)
    init_db()
    
    from .routes import main
    app.register_blueprint(main)
    
    return app
