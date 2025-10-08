# AI Clothing Size Recommender - Deployment Information

## Deployment Complete! ✅

Your AI-powered clothing size recommendation system is now live on AWS.

## Access URLs

### Frontend Website (React App)
**URL:** http://ai-clothing-images-unique-12345-frontend.s3-website-us-east-1.amazonaws.com

Visit this URL to test the application. You can:
1. Select gender (Male/Female/Unisex)
2. Upload a full-body photo
3. Get instant size recommendations with confidence scores

### Backend API
**Endpoint:** https://y1pkxt85mk.execute-api.us-east-1.amazonaws.com/prod/

API Routes:
- `POST /analyze` - Analyze photo and get size recommendation
- `POST /analyze-with-custom-chart` - Use custom size charts
- `GET /health` - Health check endpoint

## Architecture Overview

```
┌──────────────┐         ┌─────────────────┐         ┌──────────────────┐
│   S3 Bucket  │◄────────│  React Frontend │────────▶│  API Gateway     │
│  (Frontend)  │         │                 │         │                  │
└──────────────┘         └─────────────────┘         └────────┬─────────┘
                                                              │
                                                              ▼
                                                    ┌──────────────────┐
                                                    │ Lambda Function  │
                                                    │ (Docker/ECR)     │
                                                    │ - MediaPipe      │
                                                    │ - OpenCV         │
                                                    │ - FastAPI        │
                                                    └────────┬─────────┘
                                                             │
                                                             ▼
                                                    ┌──────────────────┐
                                                    │   S3 Bucket      │
                                                    │  (Image Storage) │
                                                    └──────────────────┘
```

## AWS Resources Created

### Compute
- **Lambda Function:** `ai_clothing_size_recommender`
  - Memory: 3008 MB
  - Timeout: 60 seconds
  - Runtime: Python 3.11 (Docker container)
  - Ephemeral Storage: 2048 MB

### Storage
- **ECR Repository:** `ai-clothing-lambda`
  - Container image: 1.52 GB
- **S3 Buckets:**
  - `ai-clothing-images-unique-12345` (uploaded images)
  - `ai-clothing-images-unique-12345-frontend` (website hosting)

### Networking
- **API Gateway:** `ai-clothing-api`
  - Type: HTTP API
  - CORS: Enabled for all origins

### Monitoring
- **CloudWatch Log Groups:**
  - `/aws/lambda/ai_clothing_size_recommender` (7-day retention)
  - `/aws/apigateway/ai-clothing-api` (7-day retention)

## Testing the Application

### Via Web Interface
1. Open: http://ai-clothing-images-unique-12345-frontend.s3-website-us-east-1.amazonaws.com
2. Select gender
3. Upload a full-body photo (standing, front-facing works best)
4. Click "Get Size Recommendation"
5. View results including:
   - Recommended size (XS-XXL)
   - Confidence percentage
   - Body measurements
   - All size scores

### Via API (cURL)
```bash
curl -X POST https://y1pkxt85mk.execute-api.us-east-1.amazonaws.com/prod/analyze \
  -F "image=@your_photo.jpg" \
  -F "gender=male"
```

### Via Python
```python
import requests

url = "https://y1pkxt85mk.execute-api.us-east-1.amazonaws.com/prod/analyze"
files = {'image': open('photo.jpg', 'rb')}
data = {'gender': 'male'}

response = requests.post(url, files=files, data=data)
print(response.json())
```

## Cost Estimates

### Monthly Costs (estimated for 10,000 requests/month)
- Lambda: $10-15 (60s avg execution, 3GB memory)
- API Gateway: $0.01 per 1K requests = $0.10
- S3 Storage: $0.023 per GB/month
- ECR Storage: $0.10 per GB/month = $0.15
- CloudWatch Logs: $0.50-1.00

**Total: ~$11-17/month** for 10,000 requests

## Monitoring & Logs

### View Lambda Logs
```bash
aws logs tail /aws/lambda/ai_clothing_size_recommender --follow
```

### View API Gateway Logs
```bash
aws logs tail /aws/apigateway/ai-clothing-api --follow
```

### CloudWatch Metrics
- Lambda Invocations
- Lambda Duration
- Lambda Errors
- API Gateway Requests
- API Gateway 4XX/5XX Errors

## Updating the Application

### Update Backend Code
1. Make changes to `src/` files
2. Rebuild Docker image:
   ```bash
   docker build -t ai-clothing-lambda .
   ```
3. Tag and push to ECR:
   ```bash
   docker tag ai-clothing-lambda:latest 120569604641.dkr.ecr.us-east-1.amazonaws.com/ai-clothing-lambda:latest
   docker push 120569604641.dkr.ecr.us-east-1.amazonaws.com/ai-clothing-lambda:latest
   ```
4. Update Lambda:
   ```bash
   aws lambda update-function-code \
     --function-name ai_clothing_size_recommender \
     --image-uri 120569604641.dkr.ecr.us-east-1.amazonaws.com/ai-clothing-lambda:latest
   ```

### Update Frontend
1. Make changes to `frontend/src/` files
2. Rebuild:
   ```bash
   cd frontend && npm run build
   ```
3. Deploy to S3:
   ```bash
   cd build && aws s3 sync . s3://ai-clothing-images-unique-12345-frontend/ --delete
   ```

## Customizing Size Charts

You can use custom size charts via the API:

```bash
curl -X POST https://y1pkxt85mk.execute-api.us-east-1.amazonaws.com/prod/analyze-with-custom-chart \
  -F "image=@photo.jpg" \
  -F "gender=male" \
  -F 'size_chart={
    "S": {"chest": [86, 91], "waist": [71, 76], "hips": [91, 96], "inseam": [79, 81], "shoulder": [44, 46], "arm": [60, 62]},
    "M": {"chest": [91, 97], "waist": [76, 81], "hips": [96, 102], "inseam": [81, 84], "shoulder": [46, 48], "arm": [62, 64]},
    "L": {"chest": [97, 102], "waist": [81, 86], "hips": [102, 107], "inseam": [84, 86], "shoulder": [48, 50], "arm": [64, 66]}
  }'
```

## Troubleshooting

### Frontend not loading?
- Check S3 bucket public access settings
- Verify bucket website configuration
- Check browser console for errors

### API returning errors?
- Check Lambda logs in CloudWatch
- Verify image format (JPEG/PNG)
- Ensure person is visible in photo
- Check Lambda timeout (increase if needed)

### "No person detected" error?
- Ensure full body is visible
- Use front-facing photos
- Good lighting helps
- Avoid baggy clothes

## Security Considerations

### Current Setup
- API Gateway: Public (no authentication)
- S3 Frontend: Public read
- S3 Images: Private (accessed via Lambda)
- Lambda: VPC not configured

### Recommended Improvements
1. Add API authentication (API keys or Cognito)
2. Implement rate limiting
3. Add CloudFront for caching and DDoS protection
4. Enable AWS WAF for API protection
5. Implement image size/format validation
6. Add virus scanning for uploaded images

## Cleanup (To Delete All Resources)

```bash
# Delete frontend S3 contents
aws s3 rm s3://ai-clothing-images-unique-12345-frontend --recursive

# Delete uploaded images
aws s3 rm s3://ai-clothing-images-unique-12345 --recursive

# Destroy all infrastructure
cd terraform
terraform destroy -auto-approve

# Delete ECR images (if needed)
aws ecr delete-repository --repository-name ai-clothing-lambda --force
```

## Support

For issues:
1. Check CloudWatch logs
2. Review API Gateway execution logs
3. Test Lambda function directly
4. Verify ECR image is accessible

## Next Steps

1. **Add authentication** to secure the API
2. **Implement CloudFront** for better performance
3. **Add user accounts** to save sizing history
4. **Collect feedback** to improve size recommendations
5. **Fine-tune ML model** with real measurement data
6. **Add more size charts** for different brands
7. **Implement A/B testing** for recommendation algorithm
8. **Add analytics** to track usage patterns

---

**Deployment Date:** 2025-10-08
**Region:** us-east-1
**Account ID:** 120569604641
