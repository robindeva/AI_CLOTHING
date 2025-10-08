#!/bin/bash

# Build Lambda deployment package
echo "Building Lambda deployment package..."

# Create temp directory
mkdir -p build
cd build

# Install dependencies
pip install -r ../requirements.txt -t .

# Copy source code
cp -r ../src .

# Create deployment package
zip -r ../deployment.zip .

cd ..
rm -rf build

echo "Deployment package created: deployment.zip"
echo "Size: $(du -h deployment.zip | cut -f1)"
