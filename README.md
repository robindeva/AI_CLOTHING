# AI Clothing Size Recommender

An AI-powered system that analyzes customer photos to recommend clothing sizes. The system detects body keypoints, estimates measurements, and maps them to store size charts.

## Features

- **Body Keypoint Detection**: Uses MediaPipe Pose to detect body landmarks
- **Measurement Estimation**: Calculates chest, waist, hips, inseam, shoulder, and arm measurements
- **Size Recommendation**: Maps measurements to standard size charts (XS-XXL)
- **Custom Size Charts**: Support for store-specific sizing
- **Confidence Scoring**: Provides confidence level and explanation for recommendations
- **AWS Deployment**: Fully serverless architecture using Lambda, API Gateway, and S3

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Client    │────▶│ API Gateway  │────▶│   Lambda    │
│  (Upload)   │◀────│              │◀────│  Function   │
└─────────────┘     └──────────────┘     └─────────────┘
                                                │
                                                ▼
                                         ┌─────────────┐
                                         │  S3 Bucket  │
                                         │  (Images)   │
                                         └─────────────┘
```

## Project Structure

```
AI_CLOTHING/
├── src/
│   ├── api.py                  # FastAPI endpoints
│   ├── pose_detector.py        # Keypoint detection
│   ├── measurement_estimator.py # Measurement calculation
│   └── size_recommender.py     # Size recommendation engine
├── terraform/
│   ├── main.tf                 # AWS infrastructure
│   └── variables.tf            # Configuration variables
├── scripts/
│   ├── build_lambda.sh         # Build deployment package
│   └── deploy.sh               # Deploy to AWS
├── requirements.txt            # Python dependencies
└── Dockerfile                  # Lambda container image
```

## Prerequisites

- Python 3.11+
- AWS Account with credentials configured
- Terraform (for infrastructure deployment)
- Docker (optional, for container-based deployment)

## Local Development

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Locally

```bash
cd src
uvicorn api:app --reload
```

The API will be available at `http://localhost:8000`

### 3. Test API

```bash
curl -X POST http://localhost:8000/analyze \
  -F "image=@test_photo.jpg" \
  -F "gender=male"
```

## AWS Deployment

### Option 1: Automated Deployment

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Deploy everything
./scripts/deploy.sh
```

### Option 2: Manual Deployment

#### Step 1: Build Lambda Package

```bash
./scripts/build_lambda.sh
```

#### Step 2: Deploy Infrastructure

```bash
cd terraform

# Initialize Terraform
terraform init

# Review deployment plan
terraform plan

# Deploy
terraform apply
```

#### Step 3: Get API Endpoint

```bash
terraform output api_endpoint
```

### Option 3: Container-based Deployment

```bash
# Build Docker image
docker build -t ai-clothing-lambda .

# Tag for ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker tag ai-clothing-lambda:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/ai-clothing-lambda:latest

# Push to ECR
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/ai-clothing-lambda:latest
```

## API Endpoints

### POST /analyze

Analyze photo and get size recommendation.

**Parameters:**
- `image` (file): Full-body photo (JPEG/PNG)
- `gender` (string): "male", "female", or "unisex"
- `store_image` (boolean, optional): Store image in S3

**Response:**
```json
{
  "request_id": "uuid",
  "recommended_size": "M",
  "confidence": 85,
  "explanation": "Good fit. Size M is recommended for your measurements.",
  "measurements": {
    "chest": 96.5,
    "waist": 78.2,
    "hips": 98.1,
    "inseam": 81.3,
    "shoulder": 45.7,
    "arm": 63.2
  },
  "all_size_scores": {
    "XS": 45.2,
    "S": 67.8,
    "M": 85.3,
    "L": 72.1,
    "XL": 58.9,
    "XXL": 42.5
  }
}
```

### POST /analyze-with-custom-chart

Use store-specific size chart.

**Parameters:**
- `image` (file): Full-body photo
- `gender` (string): Gender category
- `size_chart` (JSON string): Custom size chart

**Size Chart Format:**
```json
{
  "S": {
    "chest": [86, 91],
    "waist": [71, 76],
    "hips": [91, 96],
    "inseam": [79, 81],
    "shoulder": [44, 46],
    "arm": [60, 62]
  },
  "M": {
    "chest": [91, 97],
    "waist": [76, 81],
    "hips": [96, 102],
    "inseam": [81, 84],
    "shoulder": [46, 48],
    "arm": [62, 64]
  }
}
```

## Configuration

### Terraform Variables

Edit `terraform/variables.tf`:

```hcl
variable "aws_region" {
  default = "us-east-1"  # Change to your region
}

variable "bucket_name" {
  default = "your-unique-bucket-name"  # Must be globally unique
}

variable "environment" {
  default = "prod"  # dev, staging, or prod
}
```

### Size Charts

Modify size charts in `src/size_recommender.py`:

```python
MENS_SIZES = {
    "S": {"chest": (86, 91), "waist": (71, 76), ...},
    "M": {"chest": (91, 97), "waist": (76, 81), ...},
    # Add more sizes
}
```

## Photo Guidelines

For best results, customer photos should:
- Show full body (head to feet)
- Be front-facing
- Have good lighting
- Wear form-fitting clothes
- Stand in neutral pose with arms slightly away from body
- Have minimal background clutter

## Cost Estimation

AWS costs (approximate):
- Lambda: ~$0.20 per 1000 requests (with 60s timeout, 2GB memory)
- API Gateway: ~$1.00 per million requests
- S3: ~$0.023 per GB/month (if storing images)
- Data Transfer: Varies by region

Typical cost: **$5-20/month** for 10,000 requests

## Scaling Considerations

- **Lambda Timeout**: Adjust based on image processing time (default: 60s)
- **Memory**: 2GB recommended for MediaPipe processing
- **Concurrent Executions**: Set reserved concurrency if needed
- **Caching**: Consider adding CloudFront for API responses
- **Image Storage**: Set S3 lifecycle policies to archive old images

## Limitations

1. **2D Analysis**: Measurements are estimated from 2D photos
2. **Scale Estimation**: Assumes average human proportions
3. **Pose Dependency**: Best results with standard poses
4. **Clothing**: Loose clothing may affect accuracy
5. **Background**: Complex backgrounds may impact detection

## Future Enhancements

- [ ] Support for multiple angles (front/side views)
- [ ] Height input for better scale estimation
- [ ] ML model fine-tuning with actual measurements
- [ ] Body shape classification
- [ ] AR try-on integration
- [ ] Historical sizing preferences
- [ ] A/B testing framework for size recommendations

## Troubleshooting

### "No person detected in image"
- Ensure full body is visible
- Check image quality and lighting
- Verify person is facing camera

### High Lambda costs
- Reduce memory allocation if possible
- Optimize image processing
- Enable Lambda reserved concurrency limits

### Inconsistent sizing
- Calibrate scale estimation with known measurements
- Fine-tune size chart ranges
- Collect feedback and adjust scoring algorithm

## License

MIT License - See LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: [Your repo URL]
- Email: [Your support email]
