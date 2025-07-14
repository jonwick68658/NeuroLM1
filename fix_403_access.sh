#!/bin/bash

# Fix 403 Forbidden errors on Cloud Run service
echo "🔍 Diagnosing 403 Forbidden errors..."

# Set project variables
PROJECT_ID="neurolm-830566"
SERVICE_NAME="neuro-lm"
REGION="us-central1"

# Check current IAM policy on Cloud Run service
echo "📋 Checking Cloud Run service IAM policy..."
gcloud run services get-iam-policy $SERVICE_NAME --region=$REGION --project=$PROJECT_ID

# Check if the service allows unauthenticated access
echo "📋 Checking service configuration..."
gcloud run services describe $SERVICE_NAME --region=$REGION --project=$PROJECT_ID --format="value(spec.traffic[0].percent, spec.traffic[0].tag)"

# Fix 1: Ensure allUsers has invoker role
echo "🔧 Adding allUsers invoker role..."
gcloud run services add-iam-policy-binding $SERVICE_NAME \
  --member="allUsers" \
  --role="roles/run.invoker" \
  --region=$REGION \
  --project=$PROJECT_ID

# Fix 2: Check organization policies
echo "📋 Checking organization policies..."
gcloud org-policies list --project=$PROJECT_ID --format="table(name, spec.rules[0].enforce)"

# Fix 3: Check if domain restriction is still active
echo "📋 Checking domain restriction policy..."
gcloud org-policies describe constraints/iam.allowedPolicyMemberDomains --project=$PROJECT_ID --format="yaml"

# Fix 4: Update the policy to explicitly allow all domains
echo "🔧 Updating domain restriction policy..."
gcloud org-policies set-policy correct_policy_override.yaml --project=$PROJECT_ID

# Fix 5: Check Cloud Run service security settings
echo "📋 Checking Cloud Run security settings..."
gcloud run services describe $SERVICE_NAME --region=$REGION --project=$PROJECT_ID --format="value(spec.template.spec.containerConcurrency, spec.template.spec.containers[0].ports[0].containerPort)"

# Test access
echo "🧪 Testing service access..."
curl -s -o /dev/null -w "%{http_code}" https://neuro-lm-79060699409.us-central1.run.app/health

echo "✅ Access fixes applied. Testing in 30 seconds..."
sleep 30
curl -s https://neuro-lm-79060699409.us-central1.run.app/health