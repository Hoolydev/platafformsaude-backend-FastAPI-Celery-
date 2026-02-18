#!/bin/sh

# Wait for MinIO to be ready
sleep 5

# Configure MinIO client
mc alias set myminio http://localhost:9000 ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD}

# Create bucket if it doesn't exist
mc mb myminio/${MINIO_BUCKET_NAME} --ignore-existing

# Set bucket policy to allow public downloads (adjust as needed)
mc anonymous set download myminio/${MINIO_BUCKET_NAME}

# Create additional buckets for different purposes
mc mb myminio/prescriptions --ignore-existing
mc mb myminio/avatars --ignore-existing
mc mb myminio/documents --ignore-existing
mc mb myminio/backups --ignore-existing

# Set policies
mc anonymous set download myminio/avatars
mc anonymous set none myminio/prescriptions
mc anonymous set none myminio/documents
mc anonymous set none myminio/backups

echo "MinIO buckets initialized successfully"
