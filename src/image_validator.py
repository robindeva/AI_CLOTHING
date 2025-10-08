import cv2
import numpy as np
from typing import Dict, Tuple, List
import math


class ImageValidator:
    """Validates image quality and pose for accurate measurements."""

    def __init__(self):
        self.min_resolution = (400, 600)  # Min width, height in pixels
        self.max_blur_threshold = 100  # Laplacian variance threshold
        self.min_keypoint_visibility = 0.7  # 70% of keypoints must be visible
        self.min_avg_visibility = 0.6  # Average visibility score

    def validate_image_quality(self, image_bytes: bytes) -> Tuple[bool, str, Dict]:
        """
        Validate image quality for measurement accuracy.

        Args:
            image_bytes: Raw image data

        Returns:
            (is_valid, error_message, quality_metrics)
        """
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            return False, "Invalid image file", {}

        quality_metrics = {}

        # Check 1: Resolution
        height, width = image.shape[:2]
        quality_metrics["resolution"] = {"width": width, "height": height}

        if width < self.min_resolution[0] or height < self.min_resolution[1]:
            return False, f"Image resolution too low. Minimum {self.min_resolution[0]}x{self.min_resolution[1]} required. Upload a higher quality photo.", quality_metrics

        # Check 2: Blur detection (using Laplacian variance)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        quality_metrics["blur_score"] = round(laplacian_var, 2)
        quality_metrics["is_blurry"] = laplacian_var < self.max_blur_threshold

        if laplacian_var < self.max_blur_threshold:
            return False, "Image is too blurry. Please take a clearer photo in good lighting.", quality_metrics

        # Check 3: Brightness
        brightness = np.mean(gray)
        quality_metrics["brightness"] = round(brightness, 2)

        if brightness < 40:
            return False, "Image is too dark. Please take a photo in better lighting.", quality_metrics
        elif brightness > 220:
            return False, "Image is overexposed. Please avoid direct sunlight or flash.", quality_metrics

        quality_metrics["overall_quality"] = "good"
        return True, "", quality_metrics

    def validate_pose_quality(self, keypoints: Dict) -> Tuple[bool, str, Dict]:
        """
        Validate pose quality for accurate measurements.

        Args:
            keypoints: Dictionary of detected keypoints with (x, y, visibility)

        Returns:
            (is_valid, error_message, pose_metrics)
        """
        pose_metrics = {}

        # Check 1: Keypoint visibility
        visibility_scores = [kp[2] for kp in keypoints.values()]
        avg_visibility = np.mean(visibility_scores)
        visible_count = sum(1 for v in visibility_scores if v > 0.5)
        total_count = len(visibility_scores)
        visibility_ratio = visible_count / total_count

        pose_metrics["average_visibility"] = round(avg_visibility, 3)
        pose_metrics["visible_keypoints"] = f"{visible_count}/{total_count}"
        pose_metrics["visibility_ratio"] = round(visibility_ratio, 3)

        if visibility_ratio < self.min_keypoint_visibility:
            return False, f"Only {visible_count}/{total_count} body parts detected. Please take a full-body photo with your entire body visible.", pose_metrics

        if avg_visibility < self.min_avg_visibility:
            return False, "Body parts are not clearly visible. Please stand in a well-lit area with your full body in frame.", pose_metrics

        # Check 2: Front-facing pose
        is_front_facing, facing_score = self._check_front_facing(keypoints)
        pose_metrics["front_facing_score"] = round(facing_score, 3)
        pose_metrics["is_front_facing"] = is_front_facing

        if not is_front_facing:
            return False, "Please face the camera directly. Angled or side poses reduce accuracy.", pose_metrics

        # Check 3: Standing straight
        is_standing_straight, posture_score = self._check_standing_straight(keypoints)
        pose_metrics["posture_score"] = round(posture_score, 3)
        pose_metrics["is_standing_straight"] = is_standing_straight

        if not is_standing_straight:
            return False, "Please stand straight with arms at your sides. Avoid leaning or sitting.", pose_metrics

        # Check 4: Full body visible
        has_full_body, missing_parts = self._check_full_body_visible(keypoints)
        pose_metrics["has_full_body"] = has_full_body
        pose_metrics["missing_parts"] = missing_parts

        if not has_full_body:
            return False, f"Missing body parts: {', '.join(missing_parts)}. Please ensure your full body is in the frame from head to toe.", pose_metrics

        pose_metrics["overall_pose_quality"] = "good"
        return True, "", pose_metrics

    def _check_front_facing(self, keypoints: Dict) -> Tuple[bool, float]:
        """
        Check if person is facing the camera.
        Uses shoulder width ratio and hip width ratio.
        """
        left_shoulder = keypoints.get("left_shoulder")
        right_shoulder = keypoints.get("right_shoulder")
        left_hip = keypoints.get("left_hip")
        right_hip = keypoints.get("right_hip")

        if not all([left_shoulder, right_shoulder, left_hip, right_hip]):
            return False, 0.0

        # Calculate shoulder width
        shoulder_width = abs(left_shoulder[0] - right_shoulder[0])

        # Calculate hip width
        hip_width = abs(left_hip[0] - right_hip[0])

        # Front-facing: shoulder and hip widths should be similar and > 0
        # If person is angled, one will be much smaller
        if shoulder_width < 20 or hip_width < 20:  # Too narrow, likely side view
            return False, 0.3

        # Calculate symmetry score
        width_ratio = min(shoulder_width, hip_width) / max(shoulder_width, hip_width)

        # Check visibility of both sides
        left_vis = (left_shoulder[2] + left_hip[2]) / 2
        right_vis = (right_shoulder[2] + right_hip[2]) / 2
        visibility_balance = min(left_vis, right_vis) / max(left_vis, right_vis) if max(left_vis, right_vis) > 0 else 0

        front_facing_score = (width_ratio + visibility_balance) / 2

        # Threshold: score > 0.7 means front-facing
        return front_facing_score > 0.7, front_facing_score

    def _check_standing_straight(self, keypoints: Dict) -> Tuple[bool, float]:
        """
        Check if person is standing straight (not leaning).
        Measures vertical alignment of shoulders and hips.
        """
        left_shoulder = keypoints.get("left_shoulder")
        right_shoulder = keypoints.get("right_shoulder")
        left_hip = keypoints.get("left_hip")
        right_hip = keypoints.get("right_hip")

        if not all([left_shoulder, right_shoulder, left_hip, right_hip]):
            return False, 0.0

        # Check shoulder level (should be horizontal)
        shoulder_slope = abs(left_shoulder[1] - right_shoulder[1])
        shoulder_width = abs(left_shoulder[0] - right_shoulder[0])
        shoulder_tilt = shoulder_slope / shoulder_width if shoulder_width > 0 else 1.0

        # Check hip level
        hip_slope = abs(left_hip[1] - right_hip[1])
        hip_width = abs(left_hip[0] - right_hip[0])
        hip_tilt = hip_slope / hip_width if hip_width > 0 else 1.0

        # Check vertical alignment (shoulders above hips)
        left_vertical_align = left_shoulder[1] < left_hip[1]  # shoulder y < hip y (y increases downward)
        right_vertical_align = right_shoulder[1] < right_hip[1]

        # Standing straight: minimal tilt and proper vertical alignment
        max_tilt = max(shoulder_tilt, hip_tilt)

        if not (left_vertical_align and right_vertical_align):
            return False, 0.3  # Not standing properly

        if max_tilt > 0.3:  # More than 30% tilt
            return False, 0.5

        # Calculate posture score (lower tilt = better)
        posture_score = max(0, 1 - max_tilt)

        return posture_score > 0.7, posture_score

    def _check_full_body_visible(self, keypoints: Dict) -> Tuple[bool, List[str]]:
        """
        Check if full body is visible (head to toe).
        """
        required_parts = {
            "nose": "head",
            "left_shoulder": "left shoulder",
            "right_shoulder": "right shoulder",
            "left_hip": "left hip",
            "right_hip": "right hip",
            "left_knee": "left knee",
            "right_knee": "right knee",
            "left_ankle": "left ankle",
            "right_ankle": "right ankle"
        }

        missing_parts = []
        visibility_threshold = 0.3  # Minimum visibility to consider "visible"

        for key, name in required_parts.items():
            keypoint = keypoints.get(key)
            if keypoint is None or keypoint[2] < visibility_threshold:
                missing_parts.append(name)

        has_full_body = len(missing_parts) == 0

        return has_full_body, missing_parts

    def get_quality_score(self, quality_metrics: Dict, pose_metrics: Dict) -> int:
        """
        Calculate overall quality score (0-100).

        Args:
            quality_metrics: Image quality metrics
            pose_metrics: Pose quality metrics

        Returns:
            Quality score from 0-100
        """
        score = 100

        # Image quality factors
        if quality_metrics.get("is_blurry", False):
            score -= 30

        brightness = quality_metrics.get("brightness", 128)
        if brightness < 60 or brightness > 200:
            score -= 20

        # Pose quality factors
        visibility_ratio = pose_metrics.get("visibility_ratio", 1.0)
        if visibility_ratio < 0.9:
            score -= int((0.9 - visibility_ratio) * 100)

        front_facing_score = pose_metrics.get("front_facing_score", 1.0)
        if front_facing_score < 0.9:
            score -= int((0.9 - front_facing_score) * 50)

        posture_score = pose_metrics.get("posture_score", 1.0)
        if posture_score < 0.9:
            score -= int((0.9 - posture_score) * 30)

        missing_parts = pose_metrics.get("missing_parts", [])
        score -= len(missing_parts) * 10

        return max(0, min(100, score))
