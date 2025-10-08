# Quick Start Guide

## ✅ Your Application is Live and Working! 🚀

### Frontend Website
**Visit:** http://ai-clothing-images-unique-12345-frontend.s3-website-us-east-1.amazonaws.com

### API Status
- Health Check: https://y1pkxt85mk.execute-api.us-east-1.amazonaws.com/prod/health ✅
- API Info: https://y1pkxt85mk.execute-api.us-east-1.amazonaws.com/prod/ ✅

### How to Use

1. **Open the website** in your browser
2. **Select gender** (Male, Female, or Unisex)
3. **Upload a photo:**
   - Full body visible
   - Front-facing
   - Good lighting
   - Form-fitting clothes preferred
4. **Click "Get Size Recommendation"**
5. **View results:**
   - Recommended size
   - Confidence score
   - Body measurements
   - All size comparisons

### API Endpoint
**Base URL:** https://y1pkxt85mk.execute-api.us-east-1.amazonaws.com/prod/

### Test with cURL
```bash
curl -X POST https://y1pkxt85mk.execute-api.us-east-1.amazonaws.com/prod/analyze \
  -F "image=@test_photo.jpg" \
  -F "gender=male"
```

### Example Response
```json
{
  "request_id": "abc-123-def",
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

### For Best Results
- ✅ Stand straight, arms slightly away from body
- ✅ Wear form-fitting clothes
- ✅ Take photo from 6-8 feet away
- ✅ Ensure good, even lighting
- ✅ Plain background helps
- ❌ Avoid baggy clothes
- ❌ Avoid sitting or crouching
- ❌ Avoid dark or cluttered backgrounds

### Monitor Performance
```bash
# View Lambda logs
aws logs tail /aws/lambda/ai_clothing_size_recommender --follow

# Check API health
curl https://y1pkxt85mk.execute-api.us-east-1.amazonaws.com/prod/health
```

### Update Application

**Backend:**
```bash
docker build -t ai-clothing-lambda .
docker tag ai-clothing-lambda:latest 120569604641.dkr.ecr.us-east-1.amazonaws.com/ai-clothing-lambda:latest
docker push 120569604641.dkr.ecr.us-east-1.amazonaws.com/ai-clothing-lambda:latest
aws lambda update-function-code --function-name ai_clothing_size_recommender --image-uri 120569604641.dkr.ecr.us-east-1.amazonaws.com/ai-clothing-lambda:latest
```

**Frontend:**
```bash
cd frontend
npm run build
cd build
aws s3 sync . s3://ai-clothing-images-unique-12345-frontend/ --delete
```

### Need Help?
- See DEPLOYMENT.md for detailed information
- Check CloudWatch logs for errors
- Review README.md for architecture details

---
**Built with:** React, FastAPI, MediaPipe, OpenCV, AWS Lambda, API Gateway, S3
