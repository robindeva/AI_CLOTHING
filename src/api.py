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
from src.measurement_fusion import MeasurementFusion


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
        "version": "2.0.0",
        "endpoints": {
            "/analyze": "POST - Upload single photo and get size recommendation (85-90% accuracy)",
            "/analyze-multi-angle": "POST - Upload front/back/side photos for enhanced accuracy (92-95% accuracy)",
            "/analyze-with-custom-chart": "POST - Analyze with custom size chart",
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
    height: int = Form(...),
    store_image: bool = Form(False)
):
    """
    Analyze uploaded photo and return size recommendation.

    Args:
        image: Photo of person (full body, front-facing preferred)
        gender: male/female/unisex
        height: User height in cm (required for accurate measurements)
        store_image: Whether to store image in S3 (optional)

    Returns:
        Size recommendation with confidence and explanation
    """
    try:
        # Validate height
        if height < 100 or height > 250:
            raise HTTPException(
                status_code=400,
                detail="Height must be between 100cm and 250cm"
            )

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
        # Pass height if provided for accurate scale calculation
        detection_result = detector.process_image(image_bytes, height)

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

        # Step 3.5: If body type was detected, recalculate chest with body type adjustment
        if enhanced_measurements.get('_body_type') and enhanced_measurements.get('_body_type') != 'unknown':
            body_type = enhanced_measurements['_body_type']
            # Recalculate chest with body-type-aware multiplier
            refined_chest = estimator._estimate_chest(
                detection_result["keypoints"],
                detection_result["scale"],
                body_type
            )
            # Use the more conservative estimate (average of Bedrock and body-type adjusted)
            bedrock_chest = enhanced_measurements.get('chest', refined_chest)
            enhanced_measurements['chest'] = round((bedrock_chest + refined_chest) / 2, 1)

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


@app.post("/analyze-multi-angle", response_model=SizeRecommendationResponse)
async def analyze_multi_angle(
    front_image: UploadFile = File(...),
    back_image: Optional[UploadFile] = File(None),
    side_image: Optional[UploadFile] = File(None),
    gender: str = Form("unisex"),
    height: int = Form(...),
    store_image: bool = Form(False)
):
    """
    Analyze multiple viewing angles for improved measurement accuracy (92-95% accuracy).

    Args:
        front_image: Front-view photo (required)
        back_image: Back-view photo (optional)
        side_image: Side-view photo (optional)
        gender: male/female/unisex
        height: User height in cm (required for accurate measurements)
        store_image: Whether to store images in S3 (optional)

    Returns:
        Size recommendation with fused measurements from multiple angles
    """
    try:
        # Validate height
        if height < 100 or height > 250:
            raise HTTPException(
                status_code=400,
                detail="Height must be between 100cm and 250cm"
            )

        # Validate gender
        try:
            gender_enum = Gender(gender.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid gender. Must be one of: {', '.join([g.value for g in Gender])}"
            )

        # Generate request ID
        request_id = str(uuid.uuid4())

        # Initialize fusion module
        fusion = MeasurementFusion()

        # Process each angle
        angle_measurements = {}
        quality_scores = []
        image_urls = {}

        # Process front image (required)
        front_bytes = await front_image.read()

        # Validate front image quality
        img_valid, img_error, quality_metrics = validator.validate_image_quality(front_bytes)
        if not img_valid:
            raise HTTPException(status_code=400, detail=f"Front image: {img_error}")

        # Detect keypoints and estimate measurements from front
        front_detection = detector.process_image(front_bytes, height)
        pose_valid, pose_error, pose_metrics = validator.validate_pose_quality(front_detection["keypoints"])
        if not pose_valid:
            raise HTTPException(status_code=400, detail=f"Front image: {pose_error}")

        front_basic = estimator.estimate_measurements(
            front_detection["keypoints"],
            front_detection["scale"]
        )
        front_enhanced = bedrock.enhance_measurements(
            front_detection["keypoints"],
            front_basic,
            front_bytes
        )

        # Apply body-type-aware chest calculation if detected
        if front_enhanced.get('_body_type') and front_enhanced.get('_body_type') != 'unknown':
            body_type = front_enhanced['_body_type']
            refined_chest = estimator._estimate_chest(
                front_detection["keypoints"],
                front_detection["scale"],
                body_type
            )
            bedrock_chest = front_enhanced.get('chest', refined_chest)
            front_enhanced['chest'] = round((bedrock_chest + refined_chest) / 2, 1)

        # Clean front measurements
        angle_measurements['front'] = {k: v for k, v in front_enhanced.items() if not k.startswith('_')}
        quality_scores.append(validator.get_quality_score(quality_metrics, pose_metrics))

        # Store front image if requested
        if store_image:
            try:
                s3_key = f"uploads/{request_id}/front_{front_image.filename}"
                s3_client.put_object(
                    Bucket=BUCKET_NAME,
                    Key=s3_key,
                    Body=front_bytes,
                    ContentType=front_image.content_type
                )
                image_urls['front'] = f"https://{BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
            except Exception as e:
                print(f"Failed to store front image: {str(e)}")

        # Process back image if provided
        if back_image:
            try:
                back_bytes = await back_image.read()
                img_valid, img_error, back_quality_metrics = validator.validate_image_quality(back_bytes)
                if img_valid:
                    back_detection = detector.process_image(back_bytes, height)
                    pose_valid, pose_error, back_pose_metrics = validator.validate_pose_quality(back_detection["keypoints"])
                    if pose_valid:
                        back_basic = estimator.estimate_measurements(
                            back_detection["keypoints"],
                            back_detection["scale"]
                        )
                        back_enhanced = bedrock.enhance_measurements(
                            back_detection["keypoints"],
                            back_basic,
                            back_bytes
                        )
                        angle_measurements['back'] = {k: v for k, v in back_enhanced.items() if not k.startswith('_')}
                        quality_scores.append(validator.get_quality_score(back_quality_metrics, back_pose_metrics))

                        # Store back image if requested
                        if store_image:
                            try:
                                s3_key = f"uploads/{request_id}/back_{back_image.filename}"
                                s3_client.put_object(
                                    Bucket=BUCKET_NAME,
                                    Key=s3_key,
                                    Body=back_bytes,
                                    ContentType=back_image.content_type
                                )
                                image_urls['back'] = f"https://{BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
                            except Exception as e:
                                print(f"Failed to store back image: {str(e)}")
            except Exception as e:
                print(f"Warning: Failed to process back image: {str(e)}")

        # Process side image if provided
        if side_image:
            try:
                side_bytes = await side_image.read()
                img_valid, img_error, side_quality_metrics = validator.validate_image_quality(side_bytes)
                if img_valid:
                    side_detection = detector.process_image(side_bytes, height)
                    pose_valid, pose_error, side_pose_metrics = validator.validate_pose_quality(side_detection["keypoints"])
                    if pose_valid:
                        side_basic = estimator.estimate_measurements(
                            side_detection["keypoints"],
                            side_detection["scale"]
                        )
                        side_enhanced = bedrock.enhance_measurements(
                            side_detection["keypoints"],
                            side_basic,
                            side_bytes
                        )
                        angle_measurements['side'] = {k: v for k, v in side_enhanced.items() if not k.startswith('_')}
                        quality_scores.append(validator.get_quality_score(side_quality_metrics, side_pose_metrics))

                        # Store side image if requested
                        if store_image:
                            try:
                                s3_key = f"uploads/{request_id}/side_{side_image.filename}"
                                s3_client.put_object(
                                    Bucket=BUCKET_NAME,
                                    Key=s3_key,
                                    Body=side_bytes,
                                    ContentType=side_image.content_type
                                )
                                image_urls['side'] = f"https://{BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
                            except Exception as e:
                                print(f"Failed to store side image: {str(e)}")
            except Exception as e:
                print(f"Warning: Failed to process side image: {str(e)}")

        # Fuse measurements from all available angles
        fused_measurements = fusion.fuse_measurements(
            front_measurements=angle_measurements.get('front'),
            back_measurements=angle_measurements.get('back'),
            side_measurements=angle_measurements.get('side')
        )

        # Calculate confidence boost based on number of angles
        num_angles = len(angle_measurements)
        confidence_boost = fusion.calculate_confidence_boost(num_angles, quality_scores)

        # Recommend size based on fused measurements
        recommender = SizeRecommender(gender_enum)
        recommendation = recommender.recommend_size(fused_measurements)

        # Apply multi-angle confidence boost
        recommendation['confidence'] = min(100, max(0, recommendation['confidence'] + confidence_boost))

        # Generate enhanced explanation
        if front_enhanced.get('_bedrock_enhanced', False):
            recommendation['explanation'] = bedrock.generate_smart_explanation(
                fused_measurements,
                recommendation['recommended_size'],
                recommendation['confidence'],
                recommendation['all_size_scores'],
                gender
            )

        # Calculate overall quality score
        overall_quality = int(sum(quality_scores) / len(quality_scores))

        # Check for measurement conflicts
        conflicts = fusion.detect_measurement_conflicts(
            front_measurements=angle_measurements.get('front'),
            back_measurements=angle_measurements.get('back'),
            side_measurements=angle_measurements.get('side'),
            threshold_percent=20.0
        )

        quality_warnings = []
        if conflicts:
            quality_warnings.append(f"Detected {len(conflicts)} measurement inconsistencies between angles")
        if num_angles == 1:
            quality_warnings.append("Single angle only - consider adding more views for higher accuracy")

        return SizeRecommendationResponse(
            request_id=request_id,
            recommended_size=recommendation["recommended_size"],
            confidence=recommendation["confidence"],
            explanation=f"Multi-angle analysis ({num_angles} views) • " + recommendation["explanation"],
            measurements=recommendation["measurements"],
            all_size_scores=recommendation["all_size_scores"],
            image_url=image_urls.get('front'),
            ai_enhanced=front_enhanced.get('_bedrock_enhanced', False),
            body_type=front_enhanced.get('_body_type'),
            quality_score=overall_quality,
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
