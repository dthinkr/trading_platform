#!/bin/sh
set -e

echo "Firebase Project ID: $FIREBASE_PROJECT_ID"
echo "Using Firebase Token (first 10 characters): ${FIREBASE_TOKEN:0:10}..."

# Function to deploy (build already done in Docker image)
deploy_to_firebase() {
  echo "Deploying pre-built app to Firebase..."
  echo "Deploying to Firebase hosting..."
  firebase deploy --only hosting --token "$FIREBASE_TOKEN" --project "$FIREBASE_PROJECT_ID"
}

# Deploy to Firebase
deploy_to_firebase

echo "Frontend deployed to Firebase hosting successfully!"
echo "The frontend is now live on Firebase hosting and can connect to the backend API."