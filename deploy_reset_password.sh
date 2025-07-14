#!/bin/bash

# Deploy with password reset functionality directly to GCP
# This bypasses git and deploys the current code with the fixed password

echo "🚀 Deploying NeuroLM with password reset functionality..."

# Create a temporary deployment directory
mkdir -p /tmp/neurolm_deploy
cp -r . /tmp/neurolm_deploy/
cd /tmp/neurolm_deploy/

# Ensure we're using the right project
gcloud config set project neurolm-830566

# Deploy directly from source
echo "🔧 Deploying to Cloud Run..."
gcloud run deploy neuro-lm \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --port 5000 \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 1 \
  --max-instances 100 \
  --timeout 300 \
  --project neurolm-830566

echo "✅ Deployment complete!"
echo "🔗 Service URL: https://neuro-lm-79060699409.us-central1.run.app"
echo "👤 Login credentials:"
echo "   Username: Ryan"
echo "   Password: test123456"
echo "   Email: ryantodd306@gmail.com"

# Clean up
cd /
rm -rf /tmp/neurolm_deploy

echo "🧪 Testing deployment..."
sleep 10
curl -s https://neuro-lm-79060699409.us-central1.run.app/login | head -5