#!/bin/bash

# Fix authentication mismatch between repository and container deployments
# This script fixes the exact issue shown in the screenshot

set -e

PROJECT_ID="neurolm-830566"
SERVICE_NAME="neuro-lm"
REGION="us-central1"

echo "🔧 Fixing authentication mismatch for NeuroLM Cloud Run service"
echo "Issue: Repository deployment allows unauthenticated, but container deployment shows 'All'"
echo "Solution: Update container deployment to explicitly allow unauthenticated access"

# Set the project
gcloud config set project $PROJECT_ID

# Fix 1: Update the Cloud Run service to allow unauthenticated access
echo "🔧 Setting Cloud Run service to allow unauthenticated access..."
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --allow-unauthenticated

# Fix 2: Add allUsers invoker role to ensure public access
echo "🔧 Adding allUsers invoker role..."
gcloud run services add-iam-policy-binding $SERVICE_NAME \
  --member="allUsers" \
  --role="roles/run.invoker" \
  --region=$REGION

# Fix 3: Verify the authentication setting
echo "📋 Verifying authentication settings..."
gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --format="value(spec.template.metadata.annotations.'run.googleapis.com/ingress')" || echo "No ingress annotation found"

# Fix 4: Check IAM policy
echo "📋 Checking IAM policy..."
gcloud run services get-iam-policy $SERVICE_NAME --region=$REGION

# Fix 5: Redeploy with explicit authentication settings
echo "🔧 Redeploying with explicit authentication settings..."
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --allow-unauthenticated \
  --ingress=all \
  --port=5000

# Test the service
echo "🧪 Testing service access..."
SERVICE_URL="https://neuro-lm-79060699409.us-central1.run.app"

echo "Testing health endpoint:"
curl -s -w "HTTP Status: %{http_code}\n" $SERVICE_URL/health

echo "Testing login endpoint:"
curl -s -w "HTTP Status: %{http_code}\n" $SERVICE_URL/login > /dev/null

echo "✅ Authentication mismatch fix completed!"
echo "🔗 Service URL: $SERVICE_URL"
echo "📝 The service should now show 'Allow unauthenticated' for both deployments"