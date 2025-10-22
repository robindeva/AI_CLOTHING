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
            "arm": 1.0,
            "neck": 1.0,
            "wrist": 1.0,
            "thigh": 1.0,
            "calf": 1.0,
            "bicep": 1.0,
            "torso_length": 1.0,
            "back_width": 1.0,
            "rise": 1.0,
            "ankle": 1.0
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

        # NEW MEASUREMENTS (9 additional)
        # Neck circumference
        measurements["neck"] = self._estimate_neck(keypoints, scale)

        # Wrist circumference
        measurements["wrist"] = self._estimate_wrist(keypoints, scale)

        # Thigh circumference
        measurements["thigh"] = self._estimate_thigh(keypoints, scale)

        # Calf circumference
        measurements["calf"] = self._estimate_calf(keypoints, scale)

        # Bicep circumference
        measurements["bicep"] = self._estimate_bicep(keypoints, scale)

        # Torso length (shoulder to waist)
        measurements["torso_length"] = self._estimate_torso_length(keypoints, scale)

        # Back width
        measurements["back_width"] = self._estimate_back_width(keypoints, scale)

        # Rise (waist to crotch)
        measurements["rise"] = self._estimate_rise(keypoints, scale)

        # Ankle circumference
        measurements["ankle"] = self._estimate_ankle(keypoints, scale)

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

    def _estimate_neck(self, keypoints: Dict, scale: float) -> float:
        """
        Estimate neck circumference.

        Approach: Use shoulder width as proxy (neck circumference is typically 40-45% of shoulder width)
        """
        left_shoulder = keypoints["left_shoulder"]
        right_shoulder = keypoints["right_shoulder"]

        shoulder_width_px = self._calculate_distance(left_shoulder, right_shoulder)
        shoulder_width_cm = shoulder_width_px / scale

        # Apply MediaPipe joint-to-edge correction
        shoulder_width_cm = shoulder_width_cm * 1.17

        # Neck circumference is typically 85-95% of shoulder width
        # Average multiplier: 0.90 (adjusted for typical adult measurements)
        neck_circumference = shoulder_width_cm * 0.90

        return round(neck_circumference, 1)

    def _estimate_wrist(self, keypoints: Dict, scale: float) -> float:
        """
        Estimate wrist circumference.

        Approach: Use forearm length as proxy (wrist circumference is ~10% of forearm length)
        """
        # Average both wrists for accuracy
        left_elbow = keypoints["left_elbow"]
        left_wrist = keypoints["left_wrist"]
        right_elbow = keypoints["right_elbow"]
        right_wrist = keypoints["right_wrist"]

        left_forearm_px = self._calculate_distance(left_elbow, left_wrist)
        right_forearm_px = self._calculate_distance(right_elbow, right_wrist)

        avg_forearm_px = (left_forearm_px + right_forearm_px) / 2
        forearm_length_cm = avg_forearm_px / scale

        # Wrist circumference is typically 60-65% of forearm length
        # Average multiplier: 0.62 (adjusted for typical adult measurements)
        wrist_circumference = forearm_length_cm * 0.62

        return round(wrist_circumference, 1)

    def _estimate_thigh(self, keypoints: Dict, scale: float) -> float:
        """
        Estimate thigh circumference.

        Approach: Use hip width as proxy (thigh circumference is typically 1.5x hip width)
        """
        left_hip = keypoints["left_hip"]
        right_hip = keypoints["right_hip"]

        hip_width_px = self._calculate_distance(left_hip, right_hip)
        hip_width_cm = hip_width_px / scale

        # Apply MediaPipe joint-to-edge correction
        hip_width_cm = hip_width_cm * 1.17

        # Thigh circumference is typically 1.5x hip width
        thigh_circumference = hip_width_cm * 1.5

        return round(thigh_circumference, 1)

    def _estimate_calf(self, keypoints: Dict, scale: float) -> float:
        """
        Estimate calf circumference.

        Approach: Use knee-ankle distance as proxy (calf is typically 15% of lower leg length)
        """
        # Average both legs
        left_knee = keypoints["left_knee"]
        left_ankle = keypoints["left_ankle"]
        right_knee = keypoints["right_knee"]
        right_ankle = keypoints["right_ankle"]

        left_lower_leg_px = self._calculate_distance(left_knee, left_ankle)
        right_lower_leg_px = self._calculate_distance(right_knee, right_ankle)

        avg_lower_leg_px = (left_lower_leg_px + right_lower_leg_px) / 2
        lower_leg_length_cm = avg_lower_leg_px / scale

        # Calf circumference is typically 85-95% of lower leg length
        # Average multiplier: 0.90 (adjusted for typical adult measurements)
        calf_circumference = lower_leg_length_cm * 0.90

        return round(calf_circumference, 1)

    def _estimate_bicep(self, keypoints: Dict, scale: float) -> float:
        """
        Estimate bicep circumference.

        Approach: Use upper arm length as proxy (bicep is typically 18% of upper arm length)
        """
        # Average both arms
        left_shoulder = keypoints["left_shoulder"]
        left_elbow = keypoints["left_elbow"]
        right_shoulder = keypoints["right_shoulder"]
        right_elbow = keypoints["right_elbow"]

        left_upper_arm_px = self._calculate_distance(left_shoulder, left_elbow)
        right_upper_arm_px = self._calculate_distance(right_shoulder, right_elbow)

        avg_upper_arm_px = (left_upper_arm_px + right_upper_arm_px) / 2
        upper_arm_length_cm = avg_upper_arm_px / scale

        # Bicep circumference is typically 95-105% of upper arm length
        # Average multiplier: 1.00 (adjusted for typical adult measurements)
        bicep_circumference = upper_arm_length_cm * 1.00

        return round(bicep_circumference, 1)

    def _estimate_torso_length(self, keypoints: Dict, scale: float) -> float:
        """
        Estimate torso length (shoulder to waist).

        Approach: Measure from shoulder midpoint to hip level (waist approximation)
        """
        left_shoulder = keypoints["left_shoulder"]
        right_shoulder = keypoints["right_shoulder"]
        left_hip = keypoints["left_hip"]
        right_hip = keypoints["right_hip"]

        # Calculate midpoint of shoulders
        shoulder_mid_x = (left_shoulder[0] + right_shoulder[0]) / 2
        shoulder_mid_y = (left_shoulder[1] + right_shoulder[1]) / 2

        # Calculate midpoint of hips (waist level)
        hip_mid_x = (left_hip[0] + right_hip[0]) / 2
        hip_mid_y = (left_hip[1] + right_hip[1]) / 2

        # Calculate torso length
        torso_length_px = self._calculate_distance(
            (shoulder_mid_x, shoulder_mid_y),
            (hip_mid_x, hip_mid_y)
        )
        torso_length_cm = torso_length_px / scale

        return round(torso_length_cm, 1)

    def _estimate_back_width(self, keypoints: Dict, scale: float) -> float:
        """
        Estimate back width.

        Approach: Use shoulder width as proxy (back width is typically 85% of shoulder width)
        """
        left_shoulder = keypoints["left_shoulder"]
        right_shoulder = keypoints["right_shoulder"]

        shoulder_width_px = self._calculate_distance(left_shoulder, right_shoulder)
        shoulder_width_cm = shoulder_width_px / scale

        # Apply MediaPipe joint-to-edge correction
        shoulder_width_cm = shoulder_width_cm * 1.17

        # Back width is typically 85% of shoulder width
        back_width = shoulder_width_cm * 0.85

        return round(back_width, 1)

    def _estimate_rise(self, keypoints: Dict, scale: float) -> float:
        """
        Estimate rise (waist to crotch measurement).

        Approach: Calculate from hip level (waist) to midpoint between hips (crotch approximation)
        """
        left_hip = keypoints["left_hip"]
        right_hip = keypoints["right_hip"]

        # Hip midpoint approximates crotch point
        hip_mid_y = (left_hip[1] + right_hip[1]) / 2

        # Approximate waist position (slightly above hips)
        # Waist is typically 10-12cm above hip level
        # Using scale to convert to pixels
        waist_offset_cm = 11  # Average waist-to-hip distance
        waist_offset_px = waist_offset_cm * scale
        waist_y = hip_mid_y - waist_offset_px

        # Rise is the vertical distance
        rise_px = abs(hip_mid_y - waist_y)
        rise_cm = rise_px / scale

        # Add some adjustment based on typical rise measurements
        # Actual rise includes the curved path, so add 15%
        rise_cm = rise_cm * 1.15

        return round(rise_cm, 1)

    def _estimate_ankle(self, keypoints: Dict, scale: float) -> float:
        """
        Estimate ankle circumference.

        Approach: Use lower leg length as proxy (ankle is typically 8% of lower leg length)
        """
        # Average both ankles
        left_knee = keypoints["left_knee"]
        left_ankle = keypoints["left_ankle"]
        right_knee = keypoints["right_knee"]
        right_ankle = keypoints["right_ankle"]

        left_lower_leg_px = self._calculate_distance(left_knee, left_ankle)
        right_lower_leg_px = self._calculate_distance(right_knee, right_ankle)

        avg_lower_leg_px = (left_lower_leg_px + right_lower_leg_px) / 2
        lower_leg_length_cm = avg_lower_leg_px / scale

        # Ankle circumference is typically 50-55% of lower leg length
        # Average multiplier: 0.52 (adjusted for typical adult measurements)
        ankle_circumference = lower_leg_length_cm * 0.52

        return round(ankle_circumference, 1)
