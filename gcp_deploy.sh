#!/bin/bash
# GCP Deployment Script for NeuroLM

set -e

echo "🚀 Starting NeuroLM GCP deployment..."

# Check if required environment variables are set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL not set. Please set it first:"
    echo "export DATABASE_URL='postgresql://neurolm_user:YOUR_PASSWORD@34.44.233.216:5432/neurolm'"
    exit 1
fi

if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "❌ OPENROUTER_API_KEY not set. Please set it first:"
    echo "export OPENROUTER_API_KEY='your-openrouter-api-key'"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY not set. Please set it first:"
    echo "export OPENAI_API_KEY='your-openai-api-key'"
    exit 1
fi

# Get project ID
PROJECT_ID=$(gcloud config get-value project)
echo "📝 Project ID: $PROJECT_ID"

# Enable required services
echo "🔧 Enabling required services..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Build and deploy using Cloud Build
echo "🏗️ Building and deploying with Cloud Build..."
gcloud builds submit --config cloudbuild.yaml

# Get the service URL
SERVICE_URL=$(gcloud run services describe neurolm-api --region=us-central1 --format="value(status.url)")
echo "✅ Deployment complete!"
echo "🌐 Service URL: $SERVICE_URL"

# Update environment variables
echo "🔧 Setting environment variables..."
gcloud run services update neurolm-api --region=us-central1 \
    --set-env-vars DATABASE_URL="$DATABASE_URL" \
    --set-env-vars OPENROUTER_API_KEY="$OPENROUTER_API_KEY" \
    --set-env-vars OPENAI_API_KEY="$OPENAI_API_KEY" \
    --set-env-vars SECRET_KEY="$(openssl rand -base64 32)" \
    --set-env-vars USE_POSTGRESQL="true"

echo "✅ Environment variables set!"
echo "🎉 NeuroLM is now running on GCP!"
echo "📊 Monitor at: https://console.cloud.google.com/run/detail/us-central1/neurolm-api"