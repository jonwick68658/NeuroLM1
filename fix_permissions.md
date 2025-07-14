# Fix Organization Policy Permissions

## Problem Confirmed
The Google Cloud Console shows you need the "Organization Policy Administrator" role (`roles/orgpolicy.policyAdmin`) to modify organization policies.

## Solution Steps

### Step 1: Get Organization ID
```bash
gcloud organizations list
```

### Step 2: Assign Organization Policy Administrator Role
```bash
# Replace YOUR_ORG_ID with the actual organization ID
gcloud organizations add-iam-policy-binding YOUR_ORG_ID \
  --member='user:Ryan_Todd@pythagorix.com' \
  --role='roles/orgpolicy.policyAdmin'
```

### Step 3: Verify Permission Assignment
```bash
gcloud organizations get-iam-policy YOUR_ORG_ID \
  --flatten="bindings[].members" \
  --format="table(bindings.role)" \
  --filter="bindings.members:Ryan_Todd@pythagorix.com"
```

### Step 4: Create Correct Policy Override
```bash
cat > domain_policy_fix.yaml << 'EOF'
constraint: constraints/iam.allowedPolicyMemberDomains
spec:
  rules:
  - enforce: false
EOF

gcloud resource-manager org-policies set-policy domain_policy_fix.yaml --project=neurolm-830566
```

### Step 5: Enable Cloud Run Public Access
```bash
gcloud run services update neuro-lm \
    --allow-unauthenticated \
    --region=us-central1 \
    --project=neurolm-830566
```

## Required Permissions Breakdown
- `orgpolicy.policy.get` - Read organization policies
- `orgpolicy.policies.create` - Create new organization policies  
- `orgpolicy.policies.delete` - Delete organization policies
- `orgpolicy.policies.update` - Update existing organization policies

## Alternative: Google Cloud Console Method
1. Go to Google Cloud Console
2. Select your **organization** (not project) from the dropdown
3. Go to IAM & Admin → IAM
4. Find your email and click "Edit"
5. Add role: "Organization Policy Administrator"
6. Save changes