#!/bin/bash

# Deploy password reset functionality to GCP
echo "🚀 Deploying password reset functionality to GCP..."

# Add all changes
git add .

# Commit changes
git commit -m "Add password reset functionality for user login issues - allows users to reset passwords using username and email verification"

# Push to trigger Cloud Build
git push origin main

echo "✅ Changes pushed to Git. Cloud Build will automatically deploy to GCP."
echo "📝 Changes include:"
echo "   - Password reset page at /reset-password"
echo "   - Password reset endpoint for form submission"
echo "   - Added reset link to login page"
echo "   - Enhanced login debugging"
echo ""
echo "🔗 Once deployed, you can:"
echo "   1. Go to https://neuro-lm-79060699409.us-central1.run.app/login"
echo "   2. Click 'Forgot your password? Reset it here'"
echo "   3. Enter username: Ryan"
echo "   4. Enter email: ryantodd306@gmail.com"
echo "   5. Set new password"
echo "   6. Login with new password"