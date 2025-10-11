import cv2
import mediapipe as mp
import numpy as np
from typing import Dict, List, Tuple, Optional
from PIL import Image
import io
import os


class BodyKeypointDetector:
    """Detects body keypoints and estimates scale from uploaded photos."""

    def __init__(self):
        # Set MediaPipe to use /tmp for any runtime file operations
        os.environ['MEDIAPIPE_CACHE_DIR'] = '/tmp/mediapipe'
        os.makedirs('/tmp/mediapipe', exist_ok=True)

        self.mp_pose = mp.solutions.pose
        # Use model_complexity=1 instead of 2 for faster/lighter model
        self.pose = self.mp_pose.Pose(
            static_image_mode=True,
            model_complexity=1,  # Changed from 2 to 1 (lighter model)
            enable_segmentation=False,
            min_detection_confidence=0.5
        )

    def process_image(self, image_bytes: bytes, user_height_cm: Optional[int] = None) -> Dict:
        """
        Process image and extract keypoints.

        Args:
            image_bytes: Image data as bytes
            user_height_cm: Optional user height in cm for accurate scale calculation
        """
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise ValueError("Invalid image data")

        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Process image
        results = self.pose.process(image_rgb)

        if not results.pose_landmarks:
            raise ValueError("No person detected in image")

        # Extract keypoints
        height, width = image.shape[:2]
        keypoints = self._extract_keypoints(results.pose_landmarks, width, height)

        # Estimate scale (pixels per cm) - use user height if provided
        scale = self._estimate_scale(keypoints, height, user_height_cm)

        return {
            "keypoints": keypoints,
            "scale": scale,
            "image_dimensions": {"width": width, "height": height},
            "height_provided": user_height_cm is not None,
            "height_used": user_height_cm if user_height_cm else 170
        }

    def _extract_keypoints(self, landmarks, width: int, height: int) -> Dict[str, Tuple[float, float]]:
        """Extract relevant keypoints in pixel coordinates."""
        landmark_dict = {}

        # MediaPipe Pose landmark indices
        key_landmarks = {
            "nose": 0,
            "left_shoulder": 11,
            "right_shoulder": 12,
            "left_elbow": 13,
            "right_elbow": 14,
            "left_wrist": 15,
            "right_wrist": 16,
            "left_hip": 23,
            "right_hip": 24,
            "left_knee": 25,
            "right_knee": 26,
            "left_ankle": 27,
            "right_ankle": 28
        }

        for name, idx in key_landmarks.items():
            landmark = landmarks.landmark[idx]
            landmark_dict[name] = (
                landmark.x * width,
                landmark.y * height,
                landmark.visibility
            )

        return landmark_dict

    def _estimate_scale(self, keypoints: Dict, image_height: int, user_height_cm: Optional[int] = None) -> float:
        """
        Estimate scale (pixels per cm) using user's height or average height assumption.
        Uses multiple reference points for better accuracy.

        Args:
            keypoints: Detected body keypoints
            image_height: Image height in pixels
            user_height_cm: Optional user's actual height in cm

        Returns:
            Scale factor (pixels per cm)
        """
        # Use user's height if provided, otherwise use average (170cm)
        height_to_use = user_height_cm if user_height_cm else 170

        # Method 1: Nose to ankle (more accurate for full body height)
        nose = keypoints["nose"]
        left_ankle = keypoints["left_ankle"]
        right_ankle = keypoints["right_ankle"]
        avg_ankle_y = (left_ankle[1] + right_ankle[1]) / 2

        nose_to_ankle_px = abs(avg_ankle_y - nose[1])

        # Nose to ankle is approximately 92% of total height (head top is ~8% above nose)
        estimated_cm_height = height_to_use * 0.92

        scale_method1 = nose_to_ankle_px / estimated_cm_height if estimated_cm_height > 0 else 1.0

        # Method 2: Hip to ankle for inseam reference (backup)
        left_hip = keypoints["left_hip"]
        right_hip = keypoints["right_hip"]
        avg_hip_y = (left_hip[1] + right_hip[1]) / 2

        hip_to_ankle_px = abs(avg_ankle_y - avg_hip_y)

        # Hip to ankle is approximately 45% of total height
        estimated_inseam_proportion = height_to_use * 0.45

        scale_method2 = hip_to_ankle_px / estimated_inseam_proportion if estimated_inseam_proportion > 0 else 1.0

        # Average both methods for robustness
        scale = (scale_method1 * 0.7 + scale_method2 * 0.3)

        return scale

    def __del__(self):
        """Clean up resources."""
        self.pose.close()
