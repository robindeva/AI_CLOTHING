import math
from typing import Dict, Tuple


class MeasurementEstimator:
    """Estimates body measurements from keypoints and scale."""

    def __init__(self):
        """Initialize with optional calibration factors."""
        self.calibration_factors = {
            "chest": 1.0,
            "waist": 1.0,
            "hips": 1.0,
            "inseam": 1.0,
            "shoulder": 1.0,
            "arm": 1.0
        }

    def calibrate(self, keypoints: Dict, scale: float, known_measurements: Dict[str, float]):
        """
        Calibrate the estimator using known real measurements.

        Args:
            keypoints: Dictionary of body keypoints
            scale: Pixels per centimeter
            known_measurements: Dictionary of actual measurements (e.g., {"chest": 83, "waist": 58})
        """
        # Estimate measurements without calibration
        estimated = self.estimate_measurements(keypoints, scale, apply_calibration=False)

        # Calculate calibration factors for each known measurement
        for measurement_name, actual_value in known_measurements.items():
            if measurement_name in estimated and estimated[measurement_name] > 0:
                self.calibration_factors[measurement_name] = actual_value / estimated[measurement_name]

    def estimate_measurements(self, keypoints: Dict, scale: float, body_type: str = None, apply_calibration: bool = True) -> Dict[str, float]:
        """
        Estimate body measurements in centimeters.

        Args:
            keypoints: Dictionary of body keypoints with (x, y, visibility)
            scale: Pixels per centimeter
            body_type: Optional body type (slim, athletic, average, stocky, heavy)
            apply_calibration: Whether to apply calibration factors

        Returns:
            Dictionary of measurements in cm
        """
        measurements = {}

        # Chest/Bust - estimate from shoulder width with multiplier
        measurements["chest"] = self._estimate_chest(keypoints, scale, body_type)

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

        # Apply calibration factors if enabled
        if apply_calibration:
            for key in measurements:
                if key in self.calibration_factors:
                    measurements[key] = round(measurements[key] * self.calibration_factors[key], 1)

        return measurements

    def _calculate_distance(self, point1: Tuple, point2: Tuple) -> float:
        """Calculate Euclidean distance between two points."""
        x1, y1 = point1[0], point1[1]
        x2, y2 = point2[0], point2[1]
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def _estimate_chest(self, keypoints: Dict, scale: float, body_type: str = None) -> float:
        """Estimate chest circumference from shoulder width with body type adjustment."""
        left_shoulder = keypoints["left_shoulder"]
        right_shoulder = keypoints["right_shoulder"]

        shoulder_width_px = self._calculate_distance(left_shoulder, right_shoulder)
        shoulder_width_cm = shoulder_width_px / scale

        # CRITICAL: Apply MediaPipe joint-to-edge correction before calculating chest
        # MediaPipe measures joint-to-joint, but we need outer edge-to-edge
        shoulder_width_cm = shoulder_width_cm * 1.17

        # Improved multipliers based on anthropometric research
        # Chest circumference is typically 1.85-2.2x corrected shoulder width
        if body_type:
            body_type_lower = body_type.lower()
            if "slim" in body_type_lower or "lean" in body_type_lower:
                multiplier = 1.85  # Smaller chest for slim builds
            elif "athletic" in body_type_lower or "fit" in body_type_lower:
                multiplier = 1.95  # Moderate chest for athletic builds
            elif "stocky" in body_type_lower or "heavy" in body_type_lower or "broad" in body_type_lower:
                multiplier = 2.15  # Larger chest for stocky/heavy builds
            elif "average" in body_type_lower or "medium" in body_type_lower:
                multiplier = 1.90  # Standard multiplier for average builds
            else:
                multiplier = 1.90  # Default if body type unrecognized
        else:
            # Default multiplier when body type is not provided
            multiplier = 1.90

        chest_circumference = shoulder_width_cm * multiplier

        return round(chest_circumference, 1)

    def _estimate_waist(self, keypoints: Dict, scale: float) -> float:
        """
        Estimate waist circumference from hip width and torso structure.

        Note: MediaPipe hip keypoints are at the hip joints, not outer hip points.
        Apply correction factor similar to shoulders.
        """
        left_hip = keypoints["left_hip"]
        right_hip = keypoints["right_hip"]

        hip_width_px = self._calculate_distance(left_hip, right_hip)
        hip_width_cm = hip_width_px / scale

        # Correction: MediaPipe measures joint-to-joint, actual hip width is wider
        hip_width_cm = hip_width_cm * 1.17

        # Improved waist estimation
        # Waist is typically at the narrowest point between ribs and hips
        # Natural waist circumference is roughly 2.5-2.8x actual hip width
        waist_circumference = hip_width_cm * 2.55

        return round(waist_circumference, 1)

    def _estimate_hips(self, keypoints: Dict, scale: float) -> float:
        """
        Estimate hip circumference.

        Note: MediaPipe hip keypoints are at hip joints, not outer hip points.
        Apply correction factor similar to shoulders.
        """
        left_hip = keypoints["left_hip"]
        right_hip = keypoints["right_hip"]

        hip_width_px = self._calculate_distance(left_hip, right_hip)
        hip_width_cm = hip_width_px / scale

        # Correction: MediaPipe measures joint-to-joint, actual hip width is wider
        hip_width_cm = hip_width_cm * 1.17

        # Hip circumference is approximately 2.9-3.2x actual hip width
        # Adjusted after applying 1.17x correction factor
        hip_circumference = hip_width_cm * 2.95

        return round(hip_circumference, 1)

    def _estimate_inseam(self, keypoints: Dict, scale: float) -> float:
        """Estimate inseam length (hip to ankle) accounting for leg angles."""
        # Average left and right hip positions
        left_hip = keypoints["left_hip"]
        right_hip = keypoints["right_hip"]

        # Average ankle positions
        left_ankle = keypoints["left_ankle"]
        right_ankle = keypoints["right_ankle"]

        # Calculate actual leg lengths (not just vertical distance)
        # Left leg: hip to knee to ankle
        left_knee = keypoints["left_knee"]
        left_upper = self._calculate_distance(left_hip, left_knee)
        left_lower = self._calculate_distance(left_knee, left_ankle)
        left_leg_length = left_upper + left_lower

        # Right leg
        right_knee = keypoints["right_knee"]
        right_upper = self._calculate_distance(right_hip, right_knee)
        right_lower = self._calculate_distance(right_knee, right_ankle)
        right_leg_length = right_upper + right_lower

        # Average both legs
        avg_leg_length_px = (left_leg_length + right_leg_length) / 2
        inseam_cm = avg_leg_length_px / scale

        # Inseam is typically ~95% of full leg length (accounting for crotch point)
        inseam_cm = inseam_cm * 0.95

        return round(inseam_cm, 1)

    def _estimate_shoulder(self, keypoints: Dict, scale: float) -> float:
        """
        Estimate shoulder width.

        Note: MediaPipe shoulder keypoints (11, 12) represent shoulder joints.
        Actual tailoring shoulder width (acromion-to-acromion) is wider.
        Apply correction factor of 1.17x to match real measurements.
        """
        left_shoulder = keypoints["left_shoulder"]
        right_shoulder = keypoints["right_shoulder"]

        shoulder_width_px = self._calculate_distance(left_shoulder, right_shoulder)
        shoulder_width_cm = shoulder_width_px / scale

        # Correction: MediaPipe measures joint-to-joint, but tailoring measures outer edge-to-outer edge
        # Real shoulder width is typically 1.15-1.20x joint distance (based on anthropometric data)
        shoulder_width_cm = shoulder_width_cm * 1.17

        return round(shoulder_width_cm, 1)

    def _estimate_arm_length(self, keypoints: Dict, scale: float) -> float:
        """
        Estimate arm length (shoulder to wrist) - typically sleeve length measurement.

        Note: Sleeve length for tailoring is measured from center back neck, over shoulder, to wrist.
        MediaPipe measures shoulder joint to wrist, which is shorter.
        """
        # Average both arms for better accuracy
        left_shoulder = keypoints["left_shoulder"]
        left_elbow = keypoints["left_elbow"]
        left_wrist = keypoints["left_wrist"]

        right_shoulder = keypoints["right_shoulder"]
        right_elbow = keypoints["right_elbow"]
        right_wrist = keypoints["right_wrist"]

        # Calculate left arm length
        left_upper_arm_px = self._calculate_distance(left_shoulder, left_elbow)
        left_forearm_px = self._calculate_distance(left_elbow, left_wrist)
        left_arm_length_px = left_upper_arm_px + left_forearm_px

        # Calculate right arm length
        right_upper_arm_px = self._calculate_distance(right_shoulder, right_elbow)
        right_forearm_px = self._calculate_distance(right_elbow, right_wrist)
        right_arm_length_px = right_upper_arm_px + right_forearm_px

        # Average both arms
        avg_arm_length_px = (left_arm_length_px + right_arm_length_px) / 2
        arm_length_cm = avg_arm_length_px / scale

        # Adjustment for sleeve length
        # MediaPipe measures shoulder joint to wrist (curved path along arm)
        # Size charts typically use a straighter measurement
        # Apply modest correction: multiply by 0.95 to get practical sleeve length
        arm_length_cm = arm_length_cm * 0.95

        return round(arm_length_cm, 1)
