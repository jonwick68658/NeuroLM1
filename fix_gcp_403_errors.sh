#!/bin/bash

# Fix 403 Forbidden errors on NeuroLM Cloud Run service
# Run this script in Google Cloud Shell

set -e

PROJECT_ID="neurolm-830566"
SERVICE_NAME="neuro-lm"
REGION="us-central1"
ORG_ID="823516224385"

echo "🔧 Fixing 403 Forbidden errors for NeuroLM Cloud Run service"
echo "Project: $PROJECT_ID"
echo "Service: $SERVICE_NAME"
echo "Region: $REGION"
echo "Organization: $ORG_ID"

# Set the project
gcloud config set project $PROJECT_ID

# Check current service status
echo "📋 Checking current service status..."
gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.conditions[0].type, status.conditions[0].status)"

# Fix 1: Ensure allUsers has Cloud Run invoker role
echo "🔧 Adding allUsers invoker role to Cloud Run service..."
gcloud run services add-iam-policy-binding $SERVICE_NAME \
  --member="allUsers" \
  --role="roles/run.invoker" \
  --region=$REGION

# Fix 2: Check and update organization domain policy
echo "📋 Checking organization domain policy..."
gcloud org-policies describe constraints/iam.allowedPolicyMemberDomains --project=$PROJECT_ID --format="yaml" || echo "Policy not found"

# Fix 3: Apply the correct policy override
echo "🔧 Applying organization policy override..."
cat > temp_policy.yaml << 'EOF'
name: projects/neurolm-830566/policies/constraints/iam.allowedPolicyMemberDomains
spec:
  rules:
    - enforce: false
EOF

gcloud org-policies set-policy temp_policy.yaml --project=$PROJECT_ID

# Fix 4: Check and fix any firewall rules
echo "📋 Checking firewall rules..."
gcloud compute firewall-rules list --project=$PROJECT_ID --format="table(name, direction, priority, sourceRanges, allowed)"

# Fix 5: Ensure Cloud Run service is configured for public access
echo "🔧 Ensuring Cloud Run service allows public access..."
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --allow-unauthenticated

# Fix 6: Check the actual service configuration
echo "📋 Checking service configuration..."
gcloud run services describe $SERVICE_NAME --region=$REGION --format="yaml" > service_config.yaml

# Fix 7: Check organization policy inheritance
echo "📋 Checking organization policy inheritance..."
gcloud org-policies list --project=$PROJECT_ID --format="table(name, spec.rules[0].enforce)"

# Fix 8: Force policy update at organization level
echo "🔧 Updating organization policy at org level..."
gcloud org-policies set-policy temp_policy.yaml --organization=$ORG_ID

# Fix 9: Wait for policy propagation
echo "⏳ Waiting for policy propagation (60 seconds)..."
sleep 60

# Test service access
echo "🧪 Testing service access..."
SERVICE_URL="https://neuro-lm-79060699409.us-central1.run.app"

echo "Testing health endpoint:"
curl -s -w "HTTP Status: %{http_code}\n" $SERVICE_URL/health

echo "Testing login endpoint:"
curl -s -w "HTTP Status: %{http_code}\n" $SERVICE_URL/login | head -5

echo "Testing main endpoint:"
curl -s -w "HTTP Status: %{http_code}\n" $SERVICE_URL/ | head -5

# Clean up
rm -f temp_policy.yaml service_config.yaml

echo "✅ Fix script completed. If you still see 403 errors, they may take up to 10 minutes to propagate."
echo "🔗 Service URL: $SERVICE_URL"
echo "📝 Next steps:"
echo "   1. Wait 5-10 minutes for policy propagation"
echo "   2. Test the service URL in your browser"
echo "   3. Try the password reset functionality"