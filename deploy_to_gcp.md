# Deploy NeuroLM to Google Cloud Platform

## Step 1: Open Google Cloud Shell

1. Go to https://console.cloud.google.com/
2. Click the **Cloud Shell** icon (>_) in the top right
3. Wait for Cloud Shell to start

## Step 2: Upload Project Files

In Cloud Shell, create a new directory and upload files:

```bash
# Create project directory
mkdir neurolm-gcp
cd neurolm-gcp

# Create all required files (copy-paste each file below)
```

## Step 3: Create Required Files

Create these files in Cloud Shell one by one:

### 1. main_gcp.py
```python
# Copy the entire content from main_gcp.py in your Replit project
```

### 2. Dockerfile.gcp
```dockerfile
# Copy the entire content from Dockerfile.gcp in your Replit project
```

### 3. cloudbuild.yaml
```yaml
# Copy the entire content from cloudbuild.yaml in your Replit project
```

### 4. requirements.txt
```txt
# Copy the entire content from pyproject.toml dependencies
```

### 5. All your other Python files
- main.py
- intelligent_memory.py
- intelligent_memory_dual.py
- postgresql_memory_adapter.py
- model_service.py
- background_riai.py
- tool_executor.py
- tool_generator.py

### 6. All your HTML/CSS/JS files
- chat.html
- mobile.html
- landing.html
- static/ folder contents

## Step 4: Set Environment Variables

```bash
# Replace with your actual values
export DATABASE_URL="postgresql://neurolm_user:YOUR_PASSWORD@34.44.233.216:5432/neurolm"
export OPENROUTER_API_KEY="your-actual-openrouter-key"
export OPENAI_API_KEY="your-actual-openai-key"
```

## Step 5: Deploy to Cloud Run

```bash
# Deploy with Cloud Build
gcloud builds submit --config cloudbuild.yaml

# Get the service URL
gcloud run services describe neurolm-api --region=us-central1 --format="value(status.url)"
```

## Alternative: Use Cloud Shell Editor

1. In Cloud Shell, click **Open Editor**
2. Use the file upload feature to upload your entire project
3. Then run the deployment commands

Would you like me to create a deployment package for you?