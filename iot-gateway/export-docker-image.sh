#!/bin/bash

# Define image name
IMAGE_NAME="iot-gateway"

# Generate version based on timestamp (YYYYMMDD-HHMM)
VERSION="1.1.0"

# Build and tag the image
echo "Building Docker image..."
docker build -t ${IMAGE_NAME}:${VERSION} .

# Save the image to a tar file
EXPORT_DIR="../container-registry-backup"
mkdir -p $EXPORT_DIR
EXPORT_PATH="${EXPORT_DIR}/${IMAGE_NAME}_${VERSION}.tar"

echo "Saving Docker image to $EXPORT_PATH..."
docker save -o $EXPORT_PATH ${IMAGE_NAME}:${VERSION}

echo "Export completed!"
