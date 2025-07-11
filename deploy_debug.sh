#!/bin/bash
# Debug deployment script

echo "🔍 Debugging NeuroLM deployment..."

# Check current directory and files
echo "📁 Current directory: $(pwd)"
echo "📄 Files present:"
ls -la

# Check if we have all required files
echo "✅ Checking required files..."
for file in "requirements.txt" "Dockerfile" "cloudbuild.yaml" "main_gcp.py"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ $file missing"
    fi
done

# Check Cloud Build API
echo "🔧 Checking Cloud Build API..."
gcloud services list --enabled | grep cloudbuild || echo "❌ Cloud Build API not enabled"

# Check project configuration
echo "📊 Project info:"
echo "Project ID: $(gcloud config get-value project)"
echo "Account: $(gcloud config get-value account)"
echo "Region: $(gcloud config get-value compute/region)"

# Check environment variables
echo "🌍 Environment variables:"
echo "DATABASE_URL: ${DATABASE_URL:0:30}..."
echo "OPENROUTER_API_KEY: ${OPENROUTER_API_KEY:0:20}..."
echo "OPENAI_API_KEY: ${OPENAI_API_KEY:0:20}..."

# Try deployment with full verbose output
echo "🚀 Attempting deployment..."
gcloud builds submit --config cloudbuild.yaml --verbosity=debug