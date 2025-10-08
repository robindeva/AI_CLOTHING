from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import boto3
from mangum import Mangum
import json
import uuid
from datetime import datetime

from src.pose_detector import BodyKeypointDetector
from src.measurement_estimator import MeasurementEstimator
from src.size_recommender import SizeRecommender, Gender
from src.bedrock_enhancer import BedrockEnhancer
from src.image_validator import ImageValidator


app = FastAPI(title="AI Clothing Size Recommendation API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
detector = BodyKeypointDetector()
estimator = MeasurementEstimator()
bedrock = BedrockEnhancer(enabled=True)  # Hybrid AI enhancement
validator = ImageValidator()  # Image and pose validation

# AWS S3 client (optional - for storing images)
s3_client = boto3.client('s3')
BUCKET_NAME = "ai-clothing-images"  # Change to your bucket name


class SizeRecommendationResponse(BaseModel):
    request_id: str
    recommended_size: str
    confidence: int
    explanation: str
    measurements: dict
    all_size_scores: dict
    image_url: Optional[str] = None
    ai_enhanced: Optional[bool] = False  # Whether Bedrock AI was used
    body_type: Optional[str] = None  # Detected body type from AI
    quality_score: Optional[int] = None  # Overall image/pose quality (0-100)
    quality_warnings: Optional[List[str]] = None  # Quality warnings if any


@app.get("/")
async def root():
    return {
        "message": "AI Clothing Size Recommendation API",
        "version": "1.0.0",
        "endpoints": {
            "/analyze": "POST - Upload photo and get size recommendation",
            "/health": "GET - Health check"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/analyze", response_model=SizeRecommendationResponse)
async def analyze_body_measurements(
    image: UploadFile = File(...),
    gender: str = Form("unisex"),
    store_image: bool = Form(False)
):
    """
    Analyze uploaded photo and return size recommendation.

    Args:
        image: Photo of person (full body, front-facing preferred)
        gender: male/female/unisex
        store_image: Whether to store image in S3 (optional)

    Returns:
        Size recommendation with confidence and explanation
    """
    try:
        # Validate gender
        try:
            gender_enum = Gender(gender.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid gender. Must be one of: {', '.join([g.value for g in Gender])}"
            )

        # Read image bytes
        image_bytes = await image.read()

        # Generate request ID
        request_id = str(uuid.uuid4())

        # Step 0: Validate image quality
        img_valid, img_error, quality_metrics = validator.validate_image_quality(image_bytes)
        if not img_valid:
            raise HTTPException(status_code=400, detail=img_error)

        # Step 1: Detect keypoints and estimate scale (MediaPipe)
        detection_result = detector.process_image(image_bytes)

        # Step 1.5: Validate pose quality
        pose_valid, pose_error, pose_metrics = validator.validate_pose_quality(detection_result["keypoints"])
        if not pose_valid:
            raise HTTPException(status_code=400, detail=pose_error)

        # Calculate overall quality score
        quality_score = validator.get_quality_score(quality_metrics, pose_metrics)
        quality_warnings = []

        # Add warnings for suboptimal conditions
        if quality_metrics.get("brightness", 128) < 80:
            quality_warnings.append("Photo could be brighter for better accuracy")
        if pose_metrics.get("front_facing_score", 1.0) < 0.85:
            quality_warnings.append("Face the camera more directly for improved measurements")
        if pose_metrics.get("visibility_ratio", 1.0) < 0.85:
            quality_warnings.append("Some body parts are partially hidden")

        # Step 2: Estimate basic measurements (geometric calculation)
        basic_measurements = estimator.estimate_measurements(
            detection_result["keypoints"],
            detection_result["scale"]
        )

        # Step 3: Enhance measurements with Bedrock AI (hybrid approach)
        enhanced_measurements = bedrock.enhance_measurements(
            detection_result["keypoints"],
            basic_measurements,
            image_bytes
        )

        # Extract clean measurements (remove metadata)
        measurements = {k: v for k, v in enhanced_measurements.items() if not k.startswith('_')}

        # Step 4: Recommend size based on enhanced measurements
        recommender = SizeRecommender(gender_enum)
        recommendation = recommender.recommend_size(measurements)

        # Step 5: Enhance explanation with Bedrock AI
        if enhanced_measurements.get('_bedrock_enhanced', False):
            # Boost confidence if Bedrock is confident
            confidence_boost = enhanced_measurements.get('_confidence_boost', 0)
            recommendation['confidence'] = min(100, max(0, recommendation['confidence'] + confidence_boost))

            # Generate smarter explanation
            recommendation['explanation'] = bedrock.generate_smart_explanation(
                measurements,
                recommendation['recommended_size'],
                recommendation['confidence'],
                recommendation['all_size_scores'],
                gender
            )

        # Optional: Store image in S3
        image_url = None
        if store_image:
            try:
                s3_key = f"uploads/{request_id}/{image.filename}"
                s3_client.put_object(
                    Bucket=BUCKET_NAME,
                    Key=s3_key,
                    Body=image_bytes,
                    ContentType=image.content_type
                )
                image_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
            except Exception as e:
                # Log error but don't fail the request
                print(f"Failed to store image in S3: {str(e)}")

        return SizeRecommendationResponse(
            request_id=request_id,
            recommended_size=recommendation["recommended_size"],
            confidence=recommendation["confidence"],
            explanation=recommendation["explanation"],
            measurements=recommendation["measurements"],
            all_size_scores=recommendation["all_size_scores"],
            image_url=image_url,
            ai_enhanced=enhanced_measurements.get('_bedrock_enhanced', False),
            body_type=enhanced_measurements.get('_body_type'),
            quality_score=quality_score,
            quality_warnings=quality_warnings if quality_warnings else None
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/analyze-with-custom-chart")
async def analyze_with_custom_chart(
    image: UploadFile = File(...),
    gender: str = Form("unisex"),
    size_chart: str = Form(...)
):
    """
    Analyze with store-specific size chart.

    size_chart should be JSON string with format:
    {
        "S": {"chest": [86, 91], "waist": [71, 76], ...},
        "M": {"chest": [91, 97], "waist": [76, 81], ...},
        ...
    }
    """
    try:
        # Parse custom size chart
        try:
            custom_chart = json.loads(size_chart)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid size_chart JSON format")

        # Validate gender
        try:
            gender_enum = Gender(gender.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid gender. Must be one of: {', '.join([g.value for g in Gender])}"
            )

        # Read image
        image_bytes = await image.read()
        request_id = str(uuid.uuid4())

        # Process image
        detection_result = detector.process_image(image_bytes)
        measurements = estimator.estimate_measurements(
            detection_result["keypoints"],
            detection_result["scale"]
        )

        # Use custom size chart
        recommender = SizeRecommender(gender_enum)

        # Convert list format to tuple format
        converted_chart = {}
        for size, measures in custom_chart.items():
            converted_chart[size] = {
                k: tuple(v) if isinstance(v, list) else v
                for k, v in measures.items()
            }

        recommender.set_custom_size_chart(converted_chart)
        recommendation = recommender.recommend_size(measurements)

        return SizeRecommendationResponse(
            request_id=request_id,
            recommended_size=recommendation["recommended_size"],
            confidence=recommendation["confidence"],
            explanation=recommendation["explanation"],
            measurements=recommendation["measurements"],
            all_size_scores=recommendation["all_size_scores"]
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# AWS Lambda handler
handler = Mangum(app, lifespan="off", api_gateway_base_path="/prod")
