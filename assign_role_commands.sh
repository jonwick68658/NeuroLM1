#!/bin/bash

# Assign Organization Policy Administrator role to fix domain restriction policy
# Organization ID: 823516224385
# User: Ryan_Todd@pythagorix.com

echo "Assigning Organization Policy Administrator role..."

# Step 1: Assign the role at organization level
gcloud organizations add-iam-policy-binding 823516224385 \
  --member='user:Ryan_Todd@pythagorix.com' \
  --role='roles/orgpolicy.policyAdmin'

echo "Role assigned successfully!"

# Step 2: Verify the role assignment
echo "Verifying role assignment..."
gcloud organizations get-iam-policy 823516224385 \
  --flatten="bindings[].members" \
  --format="table(bindings.role)" \
  --filter="bindings.members:Ryan_Todd@pythagorix.com"

# Step 3: Create policy override to disable domain restrictions
echo "Creating policy override..."
cat > domain_policy_override.yaml << 'EOF'
constraint: constraints/iam.allowedPolicyMemberDomains
spec:
  rules:
  - enforce: false
EOF

# Step 4: Apply the policy override
echo "Applying policy override..."
gcloud resource-manager org-policies set-policy domain_policy_override.yaml --project=neurolm-830566

# Step 5: Enable Cloud Run public access
echo "Enabling Cloud Run public access..."
gcloud run services update neuro-lm \
    --allow-unauthenticated \
    --region=us-central1 \
    --project=neurolm-830566

echo "Domain restriction policy fixed!"