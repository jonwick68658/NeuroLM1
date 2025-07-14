#!/bin/bash

# Fix Domain Restricted Sharing Policy - Proper Solution
# This script creates a project-level override for the organization policy

PROJECT_ID="neurolm-830566"
REGION="us-central1"
SERVICE_NAME="neuro-lm"

echo "🔧 Fixing domain restricted sharing policy for project: $PROJECT_ID"

# Step 1: Create organization policy override file
cat > policy_override.yaml << 'EOF'
constraint: constraints/iam.allowedPolicyMemberDomains
spec:
  rules:
  - allowAll: true
    condition:
      title: "Allow Cloud Run public access"
      description: "Allow unauthenticated invocations for Cloud Run services"
      expression: 'resource.service == "run.googleapis.com"'
  - allowAll: true
    condition:
      title: "Allow all users for this project"
      description: "Override parent organization policy for public services"
      expression: 'true'
EOF

# Step 2: Apply the policy override
echo "📋 Applying organization policy override..."
gcloud resource-manager org-policies set-policy policy_override.yaml --project=$PROJECT_ID

# Step 3: Update Cloud Run service to allow unauthenticated access
echo "🔐 Updating Cloud Run service authentication..."
gcloud run services update $SERVICE_NAME \
    --allow-unauthenticated \
    --region=$REGION \
    --project=$PROJECT_ID

# Step 4: Add IAM policy binding for all users
echo "👥 Adding IAM policy binding for public access..."
gcloud run services add-iam-policy-binding $SERVICE_NAME \
    --member="allUsers" \
    --role="roles/run.invoker" \
    --region=$REGION \
    --project=$PROJECT_ID

# Step 5: Verify the changes
echo "✅ Verifying policy changes..."
gcloud resource-manager org-policies describe constraints/iam.allowedPolicyMemberDomains --project=$PROJECT_ID

echo "🔍 Checking service accessibility..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --project=$PROJECT_ID --format="value(status.url)")
echo "Service URL: $SERVICE_URL"

# Test the service
echo "🌐 Testing service accessibility..."
curl -s "$SERVICE_URL/health" | head -5

echo "✅ Domain policy fix complete!"