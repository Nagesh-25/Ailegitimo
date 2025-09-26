FROM python:3.11-slim

WORKDIR /app
COPY . /app

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Copy service account JSON into the container
COPY legal-ai-470918-e60df435360c.json /app/service-account.json

# Env vars
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/service-account.json
ENV PORT=8080

CMD ["python", "app.py"]
