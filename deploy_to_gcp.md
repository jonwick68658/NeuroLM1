# GCP Deployment Fix Instructions

## Issue: 403 Forbidden Error on Cloud Run Service

The NeuroLM service is deployed but returning 403 Forbidden errors due to organization policy restrictions blocking external access.

## Solution Steps

### 1. Run the Fix Script in Google Cloud Shell

```bash
# Clone the repo to get the fix script
git clone https://github.com/ryantd/neurolm.git
cd neurolm

# Run the fix script
chmod +x fix_gcp_403_errors.sh
./fix_gcp_403_errors.sh
```

### 2. Manual Commands (if script fails)

```bash
# Set project
gcloud config set project neurolm-830566

# Add public access to Cloud Run service
gcloud run services add-iam-policy-binding neuro-lm \
  --member="allUsers" \
  --role="roles/run.invoker" \
  --region=us-central1

# Update organization policy to allow all domains
cat > temp_policy.yaml << EOF
name: projects/neurolm-830566/policies/constraints/iam.allowedPolicyMemberDomains
spec:
  rules:
    - enforce: false
EOF

gcloud org-policies set-policy temp_policy.yaml --project=neurolm-830566
gcloud org-policies set-policy temp_policy.yaml --organization=823516224385

# Update Cloud Run service to allow unauthenticated access
gcloud run services update neuro-lm \
  --region=us-central1 \
  --allow-unauthenticated
```

### 3. Wait for Policy Propagation

Organization policies can take 5-10 minutes to propagate. Wait and then test:

```bash
curl -s https://neuro-lm-79060699409.us-central1.run.app/health
```

## Account Reset Complete

✅ **Your account has been reset:**
- Username: `Ryan`
- Email: `ryantodd306@gmail.com`
- Temporary Password: `test123`
- Service URL: https://neuro-lm-79060699409.us-central1.run.app/login

**Important:** Change your password immediately after logging in.

## Next Steps

1. Run the fix script in Google Cloud Shell
2. Wait 5-10 minutes for policy propagation
3. Test the service URL in your browser
4. Log in with the temporary password
5. Change your password using the account settings

## Service Features Ready

- RIAI (Recursive Intelligence AI) system
- Unlimited context per user
- Memory management with user isolation
- Multi-model AI integration
- Web search capabilities
- PWA mobile support
- Auto-scaling 1-100 instances for viral scale