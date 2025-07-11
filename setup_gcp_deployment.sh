#!/bin/bash
# Setup script for NeuroLM GCP deployment

echo "🚀 Setting up NeuroLM for GCP deployment..."

# Check if we're in Cloud Shell
if [ -z "$CLOUD_SHELL" ]; then
    echo "⚠️  This script should be run in Google Cloud Shell"
    echo "Please go to https://console.cloud.google.com/ and click the Cloud Shell icon"
    exit 1
fi

# Create project directory
mkdir -p neurolm-gcp
cd neurolm-gcp

echo "📁 Created project directory: neurolm-gcp"

# Create requirements.txt
cat > requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn==0.24.0
asyncpg==0.29.0
httpx==0.25.2
openai==1.3.7
python-multipart==0.0.6
python-dotenv==1.0.0
passlib==1.7.4
itsdangerous==2.1.2
starlette==0.27.0
requests==2.31.0
pydantic==2.5.0
numpy==1.24.3
neo4j==5.15.0
psycopg2-binary==2.9.9
EOF

# Create Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create static directory
RUN mkdir -p static

# Expose port
EXPOSE 5000

# Run the GCP version
CMD ["python", "main_gcp.py"]
EOF

# Create cloudbuild.yaml
cat > cloudbuild.yaml << 'EOF'
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/neurolm-api:latest', '.']
  
  # Push the container image to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/neurolm-api:latest']
  
  # Deploy container image to Cloud Run
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'neurolm-api'
      - '--image'
      - 'gcr.io/$PROJECT_ID/neurolm-api:latest'
      - '--region'
      - 'us-central1'
      - '--platform'
      - 'managed'
      - '--allow-unauthenticated'
      - '--port'
      - '5000'
      - '--memory'
      - '2Gi'
      - '--cpu'
      - '1'
      - '--max-instances'
      - '100'
      - '--set-env-vars'
      - 'USE_POSTGRESQL=true'

images:
  - 'gcr.io/$PROJECT_ID/neurolm-api:latest'
EOF

echo "✅ Created Docker and Cloud Build configuration"
echo ""
echo "📝 Next steps:"
echo "1. Upload your Python files to this directory"
echo "2. Upload your HTML/CSS/JS files"
echo "3. Set your environment variables:"
echo "   export DATABASE_URL='postgresql://neurolm_user:YOUR_PASSWORD@34.44.233.216:5432/neurolm'"
echo "   export OPENROUTER_API_KEY='your-key'"
echo "   export OPENAI_API_KEY='your-key'"
echo "4. Run: gcloud builds submit --config cloudbuild.yaml"
echo ""
echo "💡 Use 'cloudshell edit .' to open the editor and upload files"