# Google Cloud Organization Policy Fix

## Problem
The "Domain restricted sharing" organization policy is blocking public access to Cloud Run services, even with Organization Administrator permissions.

## Root Cause Analysis
The policy is inherited from a parent organization and the "Manage policy" button is grayed out, indicating either:
1. The policy is enforced at a higher organization level
2. Additional permissions are needed beyond Organization Administrator
3. The policy is set to "inherit parent's policy" and cannot be overridden

## Proper Solutions

### Solution 1: Organization Policy Administrator Role
The user needs the specific "Organization Policy Administrator" role (not just "Organization Administrator"):

1. Go to IAM & Admin → IAM
2. Find your email address
3. Add the role: "Organization Policy Administrator" (roles/orgpolicy.policyAdmin)

### Solution 2: Modify at Organization Level
If you have org-level access:

1. Go to the organization level (not project level)
2. Navigate to IAM & Admin → Organization Policies
3. Find "Domain restricted sharing" constraint
4. Edit the policy to allow exceptions for Cloud Run

### Solution 3: Project-Level Override
Create a custom constraint that overrides the organization policy:

1. Create a custom organization policy
2. Set enforcement to "off" for your specific project
3. Apply the override at the project level

### Solution 4: Use gcloud CLI
If the web interface is restricted, use gcloud commands:

```bash
# List current policy
gcloud resource-manager org-policies describe iam.allowedPolicyMemberDomains --project=PROJECT_ID

# Create a policy override
gcloud resource-manager org-policies set-policy policy.yaml --project=PROJECT_ID
```

## Next Steps
1. First try adding the specific "Organization Policy Administrator" role
2. If that doesn't work, we'll use gcloud CLI to override the policy
3. As a last resort, we'll create a new project without organization constraints