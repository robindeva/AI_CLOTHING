#!/bin/bash

set -e

echo "=== AI Clothing Size Recommender Deployment ==="

# Step 1: Build Lambda package
echo "Step 1: Building Lambda deployment package..."
bash scripts/build_lambda.sh

# Step 2: Initialize Terraform
echo "Step 2: Initializing Terraform..."
cd terraform
terraform init

# Step 3: Plan deployment
echo "Step 3: Planning deployment..."
terraform plan -out=tfplan

# Step 4: Apply deployment
echo "Step 4: Deploying to AWS..."
terraform apply tfplan

# Step 5: Get outputs
echo "Step 5: Deployment complete!"
echo ""
echo "=== Deployment Information ==="
terraform output

echo ""
echo "Your API is ready to use!"
echo "Test with:"
echo "curl -X POST \$(terraform output -raw api_endpoint)/analyze \\"
echo "  -F 'image=@test_image.jpg' \\"
echo "  -F 'gender=male'"
