import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from google.cloud import vision, storage, bigquery
from google.oauth2 import service_account
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document

# Import config
from config import GEMINI_API_KEY, GCP_PROJECT_ID, GCS_BUCKET_NAME, BIGQUERY_DATASET, BIGQUERY_TABLE, CREDENTIALS_PATH

# Configure logging
logging.basicConfig(level=logging.INFO)

# Configure Gemini with API key (force API key mode ✅)
genai.configure(api_key=GEMINI_API_KEY)
MODEL_ID = "models/gemini-1.5-flash-latest"

app = Flask(__name__)
CORS(app)

# Initialize Google Cloud clients with service account creds only for GCP services
def initialize_clients():
    try:
        creds = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)

        clients = {
            "vision": vision.ImageAnnotatorClient(credentials=creds),
            "storage": storage.Client(project=GCP_PROJECT_ID, credentials=creds),
            "bigquery": bigquery.Client(project=GCP_PROJECT_ID, credentials=creds),
        }
        logging.info("✅ Google Cloud clients initialized with service account.")
        return clients
    except Exception as e:
        logging.error(f"❌ Could not initialize clients: {e}")
        return None

clients = initialize_clients()

# Helper to extract text
def extract_text_from_file(file_path, file_type):
    try:
        if file_type == "application/pdf":
            reader = PdfReader(file_path)
            return " ".join([page.extract_text() for page in reader.pages if page.extract_text()])
        elif file_type in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ]:
            doc = Document(file_path)
            return " ".join([para.text for para in doc.paragraphs])
        elif file_type == "text/plain":
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        return None
    except Exception as e:
        logging.error(f"❌ Error extracting text: {e}")
        return None

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Legal AI Backend is running ✅"}), 200

@app.route("/analyze", methods=["POST"])
def analyze():
    if not clients:
        return jsonify({"error": "Cloud clients not available"}), 500

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    language = request.form.get("language", "English")
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    file_path = os.path.join("/tmp", file.filename)
    file.save(file_path)

    text = extract_text_from_file(file_path, file.content_type)
    if not text:
        return jsonify({"error": "Could not extract text"}), 400

    try:
        gemini_client = genai.GenerativeModel(MODEL_ID)
        response = gemini_client.generate_content(f"Summarize this in {language}: {text[:2000]}")
        summary = response.text
        return jsonify({"summary": summary})
    except Exception as e:
        logging.error(f"❌ Error in Gemini API: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        if not data or "history" not in data or "language" not in data:
            return jsonify({"error": "Missing data for chat endpoint"}), 400

        chat_model = genai.GenerativeModel(MODEL_ID)
        chat = chat_model.start_chat(history=data["history"])
        user_question = data["history"][-1]["parts"][0]["text"]
        response = chat.send_message(f"Answer in {data['language']}: {user_question}")
        return jsonify({"response": response.text})
    except Exception as e:
        logging.error(f"❌ Error in chat endpoint: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
