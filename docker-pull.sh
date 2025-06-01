#!/bin/bash

echo "Pulling Python base image..."

# Try to pull the image a few times before giving up
MAX_ATTEMPTS=3
ATTEMPT=1

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
    echo "Attempt $ATTEMPT of $MAX_ATTEMPTS"
    if docker pull python:3.10.12-slim; then
        echo "Successfully pulled Python image"
        break
    else
        echo "Failed to pull Python image on attempt $ATTEMPT"
        if [ $ATTEMPT -lt $MAX_ATTEMPTS ]; then
            echo "Waiting 10 seconds before retrying..."
            sleep 10
        fi
        ATTEMPT=$((ATTEMPT+1))
    fi
done

if [ $ATTEMPT -gt $MAX_ATTEMPTS ]; then
    echo "Failed to pull Python image after $MAX_ATTEMPTS attempts"
    echo "Checking if image exists locally..."
    if docker image inspect python:3.10.12-slim >/dev/null 2>&1; then
        echo "Image exists locally, continuing with build"
    else
        echo "Image doesn't exist locally, build will likely fail"
        exit 1
    fi
fi

echo "Building containers with docker-compose..."
docker-compose -f docker-compose.dev.yml build --no-cache
echo "Starting containers..."
docker-compose -f docker-compose.dev.yml up -d
