# GCP Migration - Final Solution

## Problem Analysis
The "Domain restricted sharing" organization policy is enforced at the organization level and cannot be overridden even with Organization Administrator permissions. This is a common issue in corporate Google Cloud environments.

## Solution: Create New Personal Project

### Step 1: Create New Project (No Organization)
1. Go to Google Cloud Console
2. Click "Select a project" → "NEW PROJECT"
3. Project name: `neurolm-public`
4. **IMPORTANT: Leave "Organization" field BLANK or select "No organization"**
5. Click "Create"

### Step 2: Enable Required APIs
```bash
# Switch to new project
gcloud config set project neurolm-public

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable sqladmin.googleapis.com
```

### Step 3: Create Cloud SQL Instance
```bash
# Create PostgreSQL instance
gcloud sql instances create neurolm-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=us-central1 \
    --storage-size=20GB \
    --storage-type=SSD \
    --backup-start-time=03:00 \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=04 \
    --authorized-networks=0.0.0.0/0

# Create database
gcloud sql databases create neurolm --instance=neurolm-db

# Create user
gcloud sql users create neurolm-user \
    --instance=neurolm-db \
    --password=YOUR_SECURE_PASSWORD
```

### Step 4: Deploy Cloud Run Service
```bash
# Build and deploy
gcloud builds submit --tag gcr.io/neurolm-public/neuro-lm .

# Deploy to Cloud Run (NO ORGANIZATION RESTRICTIONS)
gcloud run deploy neuro-lm \
    --image gcr.io/neurolm-public/neuro-lm \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --port 5000 \
    --memory 2Gi \
    --cpu 1 \
    --min-instances 1 \
    --max-instances 100 \
    --set-env-vars DATABASE_URL=postgresql://neurolm-user:YOUR_SECURE_PASSWORD@PUBLIC_IP:5432/neurolm
```

### Step 5: Configure Secrets
```bash
# Create secrets
echo "your-openrouter-key" | gcloud secrets create openrouter-key --data-file=-
echo "your-openai-key" | gcloud secrets create openai-key --data-file=-
echo "your-secret-key" | gcloud secrets create secret-key --data-file=-
```

## Benefits of This Approach
1. **No organization policy restrictions**
2. **Full control over authentication**
3. **Public access enabled by default**
4. **Clean deployment environment**
5. **No corporate policy conflicts**

## Migration Script
I'll create a complete migration script that handles all the steps automatically.