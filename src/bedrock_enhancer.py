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

            prompt = f"""You are an expert tailor and body measurement specialist with 20+ years of experience. Your task is to analyze this photo and provide PRECISE body measurements for clothing sizing.

INITIAL MEASUREMENTS (from keypoint detection):
{json.dumps(basic_measurements, indent=2)}

YOUR TASK: Carefully analyze the photo and refine these measurements using your expert knowledge.

CRITICAL ANALYSIS STEPS:

1. CLOTHING FIT ASSESSMENT:
   - Baggy/Oversized clothing: REDUCE chest/waist/hips by 6-10cm
   - Loose fit: REDUCE by 3-5cm
   - Fitted clothing: REDUCE by 1-2cm
   - Tight/Athletic wear: Keep measurements as-is
   - Thick jackets/coats: REDUCE by 8-12cm

2. BODY PROPORTIONS CHECK:
   - Chest should be 15-25cm larger than waist for men
   - Chest should be 10-20cm larger than waist for women
   - Hips typically 2-8cm larger than waist for women
   - Shoulder width should be 35-50cm for adults
   - Flag if proportions seem unrealistic

3. CAMERA ANGLE CORRECTION:
   - Low angle (camera below chest): REDUCE vertical measurements by 5-8%
   - High angle (camera above head): INCREASE vertical measurements by 5-8%
   - Angled body (not straight-on): Adjust width measurements accordingly
   - Distance: Far photos may underestimate, close-up may overestimate

4. BODY TYPE CLASSIFICATION (be specific):
   - Athletic: Broad shoulders, defined muscles, low body fat
   - Slim/Lean: Narrow frame, minimal curves, chest-waist difference <15cm
   - Average: Moderate proportions, chest-waist difference 15-20cm
   - Curvy: Pronounced hip-to-waist ratio >0.75, fuller bust/hips
   - Plus-size: Larger overall frame, rounder proportions

5. QUALITY CHECKS:
   - Adult chest: 75-130cm (typical range)
   - Adult waist: 60-120cm (typical range)
   - Adult hips: 80-140cm (typical range)
   - Shoulder: 35-55cm (typical range)
   - Reject obvious errors (e.g., chest < waist is usually wrong)

ADJUSTMENT GUIDELINES:
- Make small adjustments (±2-5cm) if clothing looks fitted
- Make larger adjustments (±6-12cm) for baggy/oversized clothing
- If keypoint measurements look accurate, keep them (±0-2cm change)
- Set confidence_boost based on photo quality:
  * +15 to +20: Excellent photo (front-facing, good lighting, fitted clothes)
  * +5 to +10: Good photo (minor issues)
  * 0: Average photo (multiple issues present)
  * -5 to -15: Poor photo (bad angle, baggy clothes, poor lighting)

OUTPUT REQUIREMENTS:
Respond ONLY with valid JSON (no markdown, no explanations outside JSON):
{{
  "chest": <number in cm, rounded to 1 decimal>,
  "waist": <number in cm, rounded to 1 decimal>,
  "hips": <number in cm, rounded to 1 decimal>,
  "inseam": <number in cm, rounded to 1 decimal>,
  "shoulder": <number in cm, rounded to 1 decimal>,
  "arm": <number in cm, rounded to 1 decimal>,
  "confidence_boost": <integer from -20 to +20>,
  "body_type": "<athletic|slim|average|curvy|plus-size>",
  "adjustment_reason": "<explain key adjustments made, e.g., 'Reduced chest by 8cm due to baggy hoodie, adjusted for slight camera angle'>"
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

            prompt = f"""You are an expert personal stylist helping a customer understand their clothing size recommendation.

CUSTOMER MEASUREMENTS:
- Chest: {measurements.get('chest')}cm
- Waist: {measurements.get('waist')}cm
- Hips: {measurements.get('hips')}cm
- Shoulder: {measurements.get('shoulder')}cm

SIZING RESULTS:
- Recommended Size: {recommended_size}
- Confidence Level: {confidence}%
- Next Best Alternative: {alternative_size}
- Gender Category: {gender}

YOUR TASK: Write a personalized 2-3 sentence explanation that is warm, confident, and actionable.

GUIDELINES:
1. START with confidence: If confidence >85%, say "Perfect fit!" or "Great match!". If 70-85%, say "Good fit" or "We recommend". If <70%, acknowledge uncertainty.

2. EXPLAIN the reasoning: Mention which measurement(s) are most aligned with this size (e.g., "Your chest and shoulder measurements align perfectly with size M")

3. OFFER ALTERNATIVES when relevant:
   - If confidence <80%, suggest trying the alternative size
   - If customer is between sizes, mention fit preference (e.g., "If you prefer a looser fit, size L would also work well")
   - If measurements are borderline, note which measurement drove the decision

4. BE SPECIFIC AND HELPFUL:
   - Don't just say "good fit" - explain WHY
   - Reference actual body measurements when relevant
   - Sound like a knowledgeable friend, not a robot

TONE: Friendly, confident, professional but approachable

EXAMPLE GOOD RESPONSES:
- "Perfect match! Your chest (96cm) and shoulders (44cm) fit squarely in the Medium range. This size will give you a comfortable, true-to-size fit."
- "We recommend size Large based on your measurements. Your chest and hips align well with this size, though if you prefer a more fitted look, Medium could also work."
- "Size Small is your best fit! Your proportions are right in the middle of this size range. You'll get a flattering, comfortable fit without being too tight or too loose."

Respond with ONLY the explanation text (no labels, no JSON, no extra formatting)."""

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
