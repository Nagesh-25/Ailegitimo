import os
from flask import Flask, jsonify, request
from flask_cors import CORS

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GCP_CREDENTIALS_JSON = os.environ.get("GCP_CREDENTIALS_JSON")

def health():
    return jsonify({
        "status": "healthy", 
        "message": "Flask app is running",
        "gemini_configured": bool(GEMINI_API_KEY),
        "gcp_configured": bool(GCP_CREDENTIALS_JSON)
    })

# Handler for Vercel
def handler(request):
    """Handler for Vercel serverless deployment"""
    app = Flask(__name__)
    CORS(app)
    
    with app.app_context():
        with app.test_request_context(
            path=request.url,
            method=request.method,
            headers=dict(request.headers),
            data=request.get_data(),
            query_string=request.query_string
        ):
            try:
                return health()
            except Exception as e:
                return jsonify({"error": str(e)}), 500
