from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from google.cloud import vision, storage, bigquery
import PyPDF2
import docx
import os
import uuid
import datetime
import tempfile

# Import configs
from config import (
    GEMINI_API_KEY,
    CREDENTIALS_PATH,
    GCP_PROJECT_ID,
    GCS_BUCKET_NAME,
    BIGQUERY_DATASET,
    BIGQUERY_TABLE
)

app = Flask(__name__)
CORS(app)

# --- Knowledge base loading ---
BNS_KNOWLEDGE_BASE = ""
INDIAN_CONSTITUTION_KNOWLEDGE_BASE = ""

try:
    with open('bns_knowledge_base.txt', 'r', encoding='utf-8') as f:
        BNS_KNOWLEDGE_BASE = f.read()
except FileNotFoundError:
    print("⚠️ bns_knowledge_base.txt not found.")

try:
    with open('indian_constitution.txt', 'r', encoding='utf-8') as f:
        INDIAN_CONSTITUTION_KNOWLEDGE_BASE = f.read()
except FileNotFoundError:
    print("⚠️ indian_constitution.txt not found.")

LEGAL_KNOWLEDGE_BASE = f"""
--- BHARATIYA NYAYA SANHITA (BNS) ---
{BNS_KNOWLEDGE_BASE}

--- INDIAN CONSTITUTION ---
{INDIAN_CONSTITUTION_KNOWLEDGE_BASE}
"""

# --- Helper functions ---
def initialize_clients():
    """Initialize Google Cloud clients."""
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = CREDENTIALS_PATH
    try:
        clients = {
            "vision": vision.ImageAnnotatorClient(),
            "storage": storage.Client(project=GCP_PROJECT_ID),
            "bigquery": bigquery.Client(project=GCP_PROJECT_ID),
        }
        print("✅ Google Cloud clients initialized.")
        return clients
    except Exception as e:
        print(f"❌ Could not initialize clients: {e}")
        return None


def upload_to_gcs(local_file_path, storage_client, document_id, original_filename):
    try:
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob_name = f"uploads/{document_id}/{original_filename}"
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(local_file_path)
        return f"gs://{GCS_BUCKET_NAME}/{blob_name}"
    except Exception as e:
        print(f"❌ GCS upload error: {e}")
        return None


def log_to_bigquery(metadata, bq_client):
    try:
        table_id = f"{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE}"
        errors = bq_client.insert_rows_json(table_id, [metadata])
        return not errors
    except Exception as e:
        print(f"❌ BigQuery log error: {e}")
        return False


def extract_text_from_file(file_path, vision_client):
    _, ext = os.path.splitext(file_path)
    text = ""
    try:
        if ext.lower() == ".txt":
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        elif ext.lower() == ".pdf":
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = "".join([page.extract_text() or "" for page in reader.pages])
        elif ext.lower() == ".docx":
            doc = docx.Document(file_path)
            text = "\n".join([p.text for p in doc.paragraphs])
        elif ext.lower() in [".png", ".jpg", ".jpeg"]:
            with open(file_path, 'rb') as image_file:
                content = image_file.read()
            image = vision.Image(content=content)
            response = vision_client.text_detection(image=image)
            if response.text_annotations:
                text = response.text_annotations[0].description
        return text
    except Exception as e:
        print(f"❌ Extraction error: {e}")
        return None

# --- Endpoints ---
@app.route('/analyze', methods=['POST'])
def analyze_document():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    target_language = request.form.get('language', 'English')

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_client = genai.GenerativeModel('gemini-1.5-flash-latest')
        cloud_clients = initialize_clients()
        if not cloud_clients:
            return jsonify({"error": "Cloud clients not available"}), 500
    except Exception as e:
        return jsonify({"error": f"Init error: {e}"}), 500

    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        document_id = str(uuid.uuid4())
        gcs_path = upload_to_gcs(tmp_path, cloud_clients["storage"], document_id, file.filename)
        metadata = {
            "document_id": document_id,
            "filename": file.filename,
            "file_type": os.path.splitext(file.filename)[1].lower(),
            "file_size": os.path.getsize(tmp_path),
            "upload_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "UPLOADED",
            "storage_path": gcs_path,
        }
        log_to_bigquery(metadata, cloud_clients["bigquery"])

        document_text = extract_text_from_file(tmp_path, cloud_clients["vision"])
        if not document_text:
            return jsonify({"error": "Text extraction failed"}), 500

        prompt = f"""
You are an expert Indian legal assistant. Summarize in {target_language}.
Format:
### Summary
### Risk Analysis
### Key Clauses & Legal Connections
### Potential Mistakes & Ambiguities

--- Legal Knowledge Base ---
{LEGAL_KNOWLEDGE_BASE}
--- Document ---
{document_text}
"""
        response = gemini_client.generate_content(prompt)

        return jsonify({"analysis": response.text, "documentText": document_text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        os.remove(tmp_path)


@app.route('/chat', methods=['POST'])
def chat_with_document():
    data = request.get_json()
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        chat_model = genai.GenerativeModel('gemini-1.5-flash-latest')
        chat = chat_model.start_chat(history=data['history'])
        user_question = data['history'][-1]['parts'][0]['text']
        response = chat.send_message(f"Answer in {data['language']}: {user_question}")
        return jsonify({"response": response.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
