from flask import Flask
from flask_cors import CORS
from .analyze import analyze_bp
from .chat import chat_bp
from .health import health_bp

app = Flask(__name__)
CORS(app)

# Register the blueprints
app.register_blueprint(analyze_bp, url_prefix='/api')
app.register_blueprint(chat_bp, url_prefix='/api')
app.register_blueprint(health_bp, url_prefix='/api')

@app.route('/')
def home():
    return "API is running."
