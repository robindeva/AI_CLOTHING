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

    def process_image(self, image_bytes: bytes) -> Dict:
        """Process image and extract keypoints."""
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

        # Estimate scale (pixels per cm)
        scale = self._estimate_scale(keypoints, height)

        return {
            "keypoints": keypoints,
            "scale": scale,
            "image_dimensions": {"width": width, "height": height}
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

    def _estimate_scale(self, keypoints: Dict, image_height: int) -> float:
        """
        Estimate scale (pixels per cm) using average human height assumption.
        Uses shoulder-to-ankle distance as reference.
        Average human height: 170cm (adjustable based on your use case)
        """
        # Calculate average shoulder position
        left_shoulder = keypoints["left_shoulder"]
        right_shoulder = keypoints["right_shoulder"]
        shoulder_y = (left_shoulder[1] + right_shoulder[1]) / 2

        # Calculate average ankle position
        left_ankle = keypoints["left_ankle"]
        right_ankle = keypoints["right_ankle"]
        ankle_y = (left_ankle[1] + right_ankle[1]) / 2

        # Distance in pixels
        pixel_height = abs(ankle_y - shoulder_y)

        # Assume shoulder to ankle is approximately 75% of total height
        # Average human height: 170cm
        estimated_cm_height = 170 * 0.75  # ~127.5 cm

        # Calculate scale: pixels per cm
        scale = pixel_height / estimated_cm_height if estimated_cm_height > 0 else 1.0

        return scale

    def __del__(self):
        """Clean up resources."""
        self.pose.close()
