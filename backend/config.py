import os

# Gemini uses API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Service account file path (used only for GCP clients, not Gemini)
CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/app/service-account.json")

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
BIGQUERY_DATASET = os.getenv("BIGQUERY_DATASET", "legal_documents")
BIGQUERY_TABLE = os.getenv("BIGQUERY_TABLE", "document_metadata")
