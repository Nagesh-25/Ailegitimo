# backend/config.py
import os

# --- Google Gemini API ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Google Cloud Service Account Credentials ---
# Path inside the container (mounted or copied before deploy)
CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/app/service-account.json")

# --- Google Cloud Project Details ---
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
BIGQUERY_DATASET = os.getenv("BIGQUERY_DATASET", "legal_documents")
BIGQUERY_TABLE = os.getenv("BIGQUERY_TABLE", "document_metadata")
