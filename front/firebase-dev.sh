#!/bin/bash
set -e

echo "Firebase Project ID: $FIREBASE_PROJECT_ID"
echo "Using Firebase Token (first 10 characters): ${FIREBASE_TOKEN:0:10}..."

# Start the development server
yarn prod &

# Function to build and deploy
build_and_deploy() {
  echo "Building and deploying..."
  yarn build
  firebase hosting:channel:deploy development --token "$FIREBASE_TOKEN" --expires 30d
}

# Initial build and deploy
build_and_deploy

# Watch for changes and redeploy
while inotifywait -e modify,create,delete,move -r ./src; do
  build_and_deploy
done