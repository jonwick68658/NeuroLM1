#!/bin/bash

# NeuroLM GCP Deployment - New Project (No Organization Restrictions)
# This script creates a clean deployment without organization policy constraints

set -e

# Configuration
PROJECT_ID="neurolm-public-$(date +%s)"
REGION="us-central1"
SERVICE_NAME="neuro-lm"
DB_INSTANCE="neurolm-db"
DB_NAME="neurolm"
DB_USER="neurolm-user"

echo "🚀 Starting NeuroLM deployment in new project: $PROJECT_ID"

# Step 1: Create new project (NO ORGANIZATION)
echo "📋 Creating new project..."
gcloud projects create $PROJECT_ID --name="NeuroLM Public" --set-as-default

# Step 2: Enable billing (required for Cloud Run and Cloud SQL)
echo "💳 Please enable billing for project $PROJECT_ID in the Google Cloud Console"
echo "Press Enter when billing is enabled..."
read

# Step 3: Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable secretmanager.googleapis.com

# Step 4: Create Cloud SQL instance
echo "🗄️ Creating Cloud SQL instance..."
gcloud sql instances create $DB_INSTANCE \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$REGION \
    --storage-size=20GB \
    --storage-type=SSD \
    --backup-start-time=03:00 \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=04 \
    --authorized-networks=0.0.0.0/0

# Step 5: Create database and user
echo "👤 Creating database and user..."
gcloud sql databases create $DB_NAME --instance=$DB_INSTANCE

# Generate secure password
DB_PASSWORD=$(openssl rand -base64 32)
gcloud sql users create $DB_USER --instance=$DB_INSTANCE --password=$DB_PASSWORD

# Get database IP
DB_IP=$(gcloud sql instances describe $DB_INSTANCE --format="value(ipAddresses[0].ipAddress)")

# Step 6: Create secrets
echo "🔐 Creating secrets..."
echo "Enter your OpenRouter API key:"
read -s OPENROUTER_KEY
echo $OPENROUTER_KEY | gcloud secrets create openrouter-key --data-file=-

echo "Enter your OpenAI API key:"
read -s OPENAI_KEY
echo $OPENAI_KEY | gcloud secrets create openai-key --data-file=-

# Generate secret key for FastAPI
SECRET_KEY=$(openssl rand -base64 32)
echo $SECRET_KEY | gcloud secrets create secret-key --data-file=-

# Step 7: Build and deploy
echo "🏗️ Building and deploying to Cloud Run..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME --file=Dockerfile.gcp

# Deploy to Cloud Run with NO AUTHENTICATION RESTRICTIONS
gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --port 5000 \
    --memory 2Gi \
    --cpu 1 \
    --min-instances 1 \
    --max-instances 100 \
    --set-env-vars DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@$DB_IP:5432/$DB_NAME \
    --set-secrets OPENROUTER_API_KEY=openrouter-key:latest \
    --set-secrets OPENAI_API_KEY=openai-key:latest \
    --set-secrets SECRET_KEY=secret-key:latest

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format="value(status.url)")

echo "✅ Deployment complete!"
echo "🌐 Service URL: $SERVICE_URL"
echo "🗄️ Database: $DB_IP"
echo "📊 Project: $PROJECT_ID"
echo ""
echo "🎉 NeuroLM is now publicly accessible without organization restrictions!"