import boto3
import json
import base64
from typing import Dict, Optional
import os


class BedrockEnhancer:
    """
    Enhances size recommendations using AWS Bedrock in hybrid mode.
    Works alongside MediaPipe to improve accuracy with AI vision.
    """

    def __init__(self, enabled: bool = True):
        """
        Initialize Bedrock enhancer.

        Args:
            enabled: Feature flag to enable/disable Bedrock (default: True)
        """
        self.enabled = enabled and os.environ.get('ENABLE_BEDROCK', 'true').lower() == 'true'

        if self.enabled:
            try:
                self.bedrock_runtime = boto3.client(
                    service_name='bedrock-runtime',
                    region_name=os.environ.get('AWS_REGION', 'us-east-1')
                )
                self.model_id = "amazon.nova-pro-v1:0"
                print("✅ Bedrock enhancer initialized (Amazon Nova Pro)")
            except Exception as e:
                print(f"⚠️ Bedrock initialization failed: {str(e)}")
                self.enabled = False
        else:
            print("ℹ️ Bedrock enhancer disabled")

    def enhance_measurements(
        self,
        keypoints: Dict,
        basic_measurements: Dict[str, float],
        image_bytes: bytes
    ) -> Dict:
        """
        Enhance measurements using Bedrock vision analysis.
        Falls back to basic measurements if Bedrock is disabled or fails.

        Args:
            keypoints: Detected body keypoints from MediaPipe
            basic_measurements: Initial measurements from geometric calculation
            image_bytes: Original image data

        Returns:
            Enhanced measurements with metadata
        """
        if not self.enabled:
            return {
                **basic_measurements,
                "_bedrock_enhanced": False,
                "_fallback_reason": "bedrock_disabled"
            }

        try:
            # Encode image to base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')

            prompt = f"""You are an expert fashion consultant analyzing body measurements from a photo.

I have initial measurements calculated from body keypoint detection:
{json.dumps(basic_measurements, indent=2)}

Please analyze the photo and refine these measurements considering:
1. Actual body shape and proportions visible in the image
2. Whether clothing is loose/tight (affects measurement accuracy)
3. Camera angle and perspective distortion
4. Body type (athletic, slim, average, curvy, plus-size)
5. Posture and stance

Provide refined measurements in centimeters. If the initial measurements look accurate, you can keep them the same.

Respond ONLY with valid JSON (no markdown):
{{
  "chest": <number>,
  "waist": <number>,
  "hips": <number>,
  "inseam": <number>,
  "shoulder": <number>,
  "arm": <number>,
  "confidence_boost": <number -20 to +20>,
  "body_type": "<athletic|slim|average|curvy|plus-size>",
  "adjustment_reason": "<brief explanation if measurements were changed>"
}}"""

            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps({
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "image": {
                                        "format": "jpeg",
                                        "source": {
                                            "bytes": image_base64
                                        }
                                    }
                                },
                                {
                                    "text": prompt
                                }
                            ]
                        }
                    ],
                    "inferenceConfig": {
                        "max_new_tokens": 1000,
                        "temperature": 0.1
                    }
                })
            )

            response_body = json.loads(response['body'].read())
            content_text = response_body['output']['message']['content'][0]['text']

            # Parse JSON from response (handle markdown code blocks)
            json_str = self._extract_json(content_text)
            enhanced_data = json.loads(json_str)

            # Validate measurements are reasonable
            enhanced_measurements = {}
            for key in ['chest', 'waist', 'hips', 'inseam', 'shoulder', 'arm']:
                value = enhanced_data.get(key, basic_measurements[key])
                # Sanity check: don't allow >30cm deviation from basic measurements
                if abs(value - basic_measurements[key]) <= 30:
                    enhanced_measurements[key] = round(float(value), 1)
                else:
                    enhanced_measurements[key] = basic_measurements[key]

            return {
                **enhanced_measurements,
                "_bedrock_enhanced": True,
                "_confidence_boost": enhanced_data.get("confidence_boost", 0),
                "_body_type": enhanced_data.get("body_type", "unknown"),
                "_adjustment_reason": enhanced_data.get("adjustment_reason", ""),
                "_original_measurements": basic_measurements
            }

        except Exception as e:
            print(f"⚠️ Bedrock enhancement failed: {str(e)}")
            # Fallback to basic measurements
            return {
                **basic_measurements,
                "_bedrock_enhanced": False,
                "_fallback_reason": str(e)
            }

    def generate_smart_explanation(
        self,
        measurements: Dict[str, float],
        recommended_size: str,
        confidence: int,
        all_size_scores: Dict,
        gender: str = "unisex"
    ) -> str:
        """
        Generate intelligent, personalized explanation using Bedrock.
        Falls back to basic explanation if Bedrock fails.

        Args:
            measurements: Body measurements
            recommended_size: Recommended size
            confidence: Confidence score
            all_size_scores: Scores for all sizes
            gender: Customer gender

        Returns:
            Enhanced explanation text
        """
        if not self.enabled:
            return self._generate_basic_explanation(recommended_size, confidence)

        try:
            # Get the next best size
            sorted_sizes = sorted(all_size_scores.items(), key=lambda x: x[1], reverse=True)
            alternative_size = sorted_sizes[1][0] if len(sorted_sizes) > 1 else None

            prompt = f"""You are a helpful fashion stylist. A customer just got sized with these measurements:

Measurements (cm): {json.dumps(measurements, indent=2)}
Recommended Size: {recommended_size}
Confidence: {confidence}%
Gender Category: {gender}
Alternative Size: {alternative_size} (if they want different fit)

Create a friendly, helpful explanation (2-3 sentences) that:
1. Confirms the size recommendation
2. Mentions if any measurements are borderline between sizes
3. Suggests the alternative size if they prefer looser/tighter fit
4. Sounds natural and conversational

Keep it concise and helpful. Don't use technical jargon.

Respond with just the explanation text (no JSON, no extra formatting)."""

            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps({
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "text": prompt
                                }
                            ]
                        }
                    ],
                    "inferenceConfig": {
                        "max_new_tokens": 300,
                        "temperature": 0.2
                    }
                })
            )

            response_body = json.loads(response['body'].read())
            explanation = response_body['output']['message']['content'][0]['text'].strip()

            # Remove any markdown or extra formatting
            explanation = explanation.replace('```', '').strip()

            return explanation

        except Exception as e:
            print(f"⚠️ Bedrock explanation failed: {str(e)}")
            return self._generate_basic_explanation(recommended_size, confidence)

    def _extract_json(self, text: str) -> str:
        """Extract JSON from text that might contain markdown code blocks."""
        text = text.strip()

        if '```json' in text:
            return text.split('```json')[1].split('```')[0].strip()
        elif '```' in text:
            return text.split('```')[1].split('```')[0].strip()
        else:
            return text

    def _generate_basic_explanation(self, size: str, confidence: int) -> str:
        """Generate basic explanation when Bedrock is not available."""
        if confidence >= 90:
            return f"Excellent fit! Size {size} matches your measurements very closely."
        elif confidence >= 75:
            return f"Good fit. Size {size} is recommended for your measurements."
        elif confidence >= 60:
            return f"Size {size} is recommended, but fit may vary by brand."
        else:
            return f"Size {size} is the closest match. Consider trying the size above or below as well."
