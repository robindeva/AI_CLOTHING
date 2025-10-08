import math
from typing import Dict, Tuple


class MeasurementEstimator:
    """Estimates body measurements from keypoints and scale."""

    def estimate_measurements(self, keypoints: Dict, scale: float) -> Dict[str, float]:
        """
        Estimate body measurements in centimeters.

        Args:
            keypoints: Dictionary of body keypoints with (x, y, visibility)
            scale: Pixels per centimeter

        Returns:
            Dictionary of measurements in cm
        """
        measurements = {}

        # Chest/Bust - estimate from shoulder width with multiplier
        measurements["chest"] = self._estimate_chest(keypoints, scale)

        # Waist - estimate from hip width
        measurements["waist"] = self._estimate_waist(keypoints, scale)

        # Hips - measure hip width
        measurements["hips"] = self._estimate_hips(keypoints, scale)

        # Inseam - hip to ankle
        measurements["inseam"] = self._estimate_inseam(keypoints, scale)

        # Shoulder width
        measurements["shoulder"] = self._estimate_shoulder(keypoints, scale)

        # Arm length - shoulder to wrist
        measurements["arm"] = self._estimate_arm_length(keypoints, scale)

        return measurements

    def _calculate_distance(self, point1: Tuple, point2: Tuple) -> float:
        """Calculate Euclidean distance between two points."""
        x1, y1 = point1[0], point1[1]
        x2, y2 = point2[0], point2[1]
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def _estimate_chest(self, keypoints: Dict, scale: float) -> float:
        """Estimate chest circumference from shoulder width."""
        left_shoulder = keypoints["left_shoulder"]
        right_shoulder = keypoints["right_shoulder"]

        shoulder_width_px = self._calculate_distance(left_shoulder, right_shoulder)
        shoulder_width_cm = shoulder_width_px / scale

        # Chest circumference is approximately 2.5x shoulder width
        # This is an empirical approximation
        chest_circumference = shoulder_width_cm * 2.5

        return round(chest_circumference, 1)

    def _estimate_waist(self, keypoints: Dict, scale: float) -> float:
        """Estimate waist circumference from hip width."""
        left_hip = keypoints["left_hip"]
        right_hip = keypoints["right_hip"]

        hip_width_px = self._calculate_distance(left_hip, right_hip)
        hip_width_cm = hip_width_px / scale

        # Waist is typically 0.7-0.8 of hip width measurement
        # Using midpoint hip position as waist approximation
        waist_circumference = hip_width_cm * 2.3

        return round(waist_circumference, 1)

    def _estimate_hips(self, keypoints: Dict, scale: float) -> float:
        """Estimate hip circumference."""
        left_hip = keypoints["left_hip"]
        right_hip = keypoints["right_hip"]

        hip_width_px = self._calculate_distance(left_hip, right_hip)
        hip_width_cm = hip_width_px / scale

        # Hip circumference is approximately 2.5x hip width
        hip_circumference = hip_width_cm * 2.5

        return round(hip_circumference, 1)

    def _estimate_inseam(self, keypoints: Dict, scale: float) -> float:
        """Estimate inseam length (hip to ankle)."""
        # Average left and right hip positions
        left_hip = keypoints["left_hip"]
        right_hip = keypoints["right_hip"]
        avg_hip_y = (left_hip[1] + right_hip[1]) / 2

        # Average ankle positions
        left_ankle = keypoints["left_ankle"]
        right_ankle = keypoints["right_ankle"]
        avg_ankle_y = (left_ankle[1] + right_ankle[1]) / 2

        # Calculate vertical distance
        inseam_px = abs(avg_ankle_y - avg_hip_y)
        inseam_cm = inseam_px / scale

        return round(inseam_cm, 1)

    def _estimate_shoulder(self, keypoints: Dict, scale: float) -> float:
        """Estimate shoulder width."""
        left_shoulder = keypoints["left_shoulder"]
        right_shoulder = keypoints["right_shoulder"]

        shoulder_width_px = self._calculate_distance(left_shoulder, right_shoulder)
        shoulder_width_cm = shoulder_width_px / scale

        return round(shoulder_width_cm, 1)

    def _estimate_arm_length(self, keypoints: Dict, scale: float) -> float:
        """Estimate arm length (shoulder to wrist)."""
        # Use right arm as default, can average both if needed
        right_shoulder = keypoints["right_shoulder"]
        right_elbow = keypoints["right_elbow"]
        right_wrist = keypoints["right_wrist"]

        # Calculate upper arm length
        upper_arm_px = self._calculate_distance(right_shoulder, right_elbow)

        # Calculate forearm length
        forearm_px = self._calculate_distance(right_elbow, right_wrist)

        # Total arm length
        total_arm_px = upper_arm_px + forearm_px
        arm_length_cm = total_arm_px / scale

        return round(arm_length_cm, 1)
