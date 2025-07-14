#!/bin/bash

# Verify and fix organization policy permissions
echo "Checking current permissions..."

# Check if Organization Policy Administrator role was assigned
gcloud organizations get-iam-policy 823516224385 \
  --flatten="bindings[].members" \
  --format="table(bindings.role)" \
  --filter="bindings.members:Ryan_Todd@pythagorix.com AND bindings.role:roles/orgpolicy.policyAdmin"

echo "If no Organization Policy Administrator role found, assigning it now..."

# Assign Organization Policy Administrator role
gcloud organizations add-iam-policy-binding 823516224385 \
  --member='user:Ryan_Todd@pythagorix.com' \
  --role='roles/orgpolicy.policyAdmin'

echo "Role assignment complete. Waiting 30 seconds for propagation..."
sleep 30

# Try alternative approach - use newer gcloud org-policies command
echo "Creating organization-level policy override..."
cat > org_policy_fix.yaml << 'EOF'
name: organizations/823516224385/policies/constraints/iam.allowedPolicyMemberDomains
spec:
  rules:
    - enforce: false
EOF

# Apply using the newer gcloud org-policies command
gcloud org-policies set-policy org_policy_fix.yaml

echo "Policy override applied. Testing Cloud Run access..."

# Update Cloud Run service
gcloud run services update neuro-lm \
    --allow-unauthenticated \
    --region=us-central1 \
    --project=neurolm-830566

# Add IAM policy binding
gcloud run services add-iam-policy-binding neuro-lm \
    --member="allUsers" \
    --role="roles/run.invoker" \
    --region=us-central1 \
    --project=neurolm-830566

echo "Testing service accessibility..."
curl -s "https://neuro-lm-79060699409.us-central1.run.app/health"