#!/bin/bash

# Build the Docker image with Buildx
docker buildx build --platform linux/amd64 -t london-trader . --load

# Check if the build was successful
if [ $? -eq 0 ]; then
    echo "Build successful, proceeding with tagging and pushing..."

    # Tag the Docker image for Heroku
    docker tag london-trader registry.heroku.com/london-trader/web

    # Push the Docker image to Heroku Container Registry
    docker push registry.heroku.com/london-trader/web

    # Release the container (this step might be unnecessary if `docker push` already handles it. Usually, you would use `heroku container:release web` instead)
    heroku container:release web -a london-trader

    echo "Deployment successful."
else
    echo "Build failed, aborting deployment."
fi
