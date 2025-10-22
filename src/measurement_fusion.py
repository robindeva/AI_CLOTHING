"""
Multi-angle measurement fusion module.
Combines measurements from front, back, and side views for improved accuracy.
"""
from typing import Dict, List, Optional
import numpy as np


class MeasurementFusion:
    """Fuses measurements from multiple viewing angles for higher accuracy."""

    def __init__(self):
        """Initialize fusion weights for different angles and measurements."""
        # Weights for each angle based on measurement type
        # Higher weight = more reliable from that angle
        self.angle_weights = {
            'front': {
                'chest': 0.60,
                'waist': 0.55,
                'hips': 0.55,
                'shoulder': 0.70,
                'inseam': 0.50,
                'arm': 0.50,
                'neck': 0.60,
                'bicep': 0.45,
                'wrist': 0.50,
                'thigh': 0.45,
                'calf': 0.45,
                'ankle': 0.50,
                'torso_length': 0.60,
                'back_width': 0.20,  # Less reliable from front
                'rise': 0.40
            },
            'back': {
                'chest': 0.30,
                'waist': 0.35,
                'hips': 0.35,
                'shoulder': 0.80,  # Most reliable from back
                'inseam': 0.40,
                'arm': 0.40,
                'neck': 0.30,
                'bicep': 0.45,
                'wrist': 0.40,
                'thigh': 0.35,
                'calf': 0.40,
                'ankle': 0.40,
                'torso_length': 0.50,
                'back_width': 0.80,  # Most reliable from back
                'rise': 0.40
            },
            'side': {
                'chest': 0.70,  # Depth measurement from side
                'waist': 0.60,
                'hips': 0.60,
                'shoulder': 0.40,
                'inseam': 0.70,  # Most reliable from side
                'arm': 0.70,  # Most reliable from side
                'neck': 0.50,
                'bicep': 0.60,
                'wrist': 0.50,
                'thigh': 0.70,
                'calf': 0.65,
                'ankle': 0.60,
                'torso_length': 0.80,  # Most reliable from side
                'back_width': 0.40,
                'rise': 0.80  # Most reliable from side
            }
        }

    def fuse_measurements(
        self,
        front_measurements: Optional[Dict[str, float]] = None,
        back_measurements: Optional[Dict[str, float]] = None,
        side_measurements: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        Fuse measurements from multiple angles using weighted averaging.

        Args:
            front_measurements: Measurements from front view
            back_measurements: Measurements from back view
            side_measurements: Measurements from side view

        Returns:
            Fused measurements dictionary with improved accuracy
        """
        # Collect available measurements
        available_angles = {}
        if front_measurements:
            available_angles['front'] = front_measurements
        if back_measurements:
            available_angles['back'] = back_measurements
        if side_measurements:
            available_angles['side'] = side_measurements

        if not available_angles:
            raise ValueError("At least one set of measurements must be provided")

        # If only one angle is available, return it as-is
        if len(available_angles) == 1:
            angle_name = list(available_angles.keys())[0]
            return available_angles[angle_name].copy()

        # Get all measurement keys from all angles
        all_keys = set()
        for measurements in available_angles.values():
            all_keys.update(measurements.keys())

        # Fuse each measurement
        fused = {}
        for key in all_keys:
            values = []
            weights = []

            for angle, measurements in available_angles.items():
                if key in measurements:
                    value = measurements[key]
                    weight = self.angle_weights[angle].get(key, 0.5)  # Default weight 0.5
                    values.append(value)
                    weights.append(weight)

            if values:
                # Weighted average
                fused_value = np.average(values, weights=weights)
                fused[key] = round(float(fused_value), 1)

        return fused

    def calculate_confidence_boost(
        self,
        num_angles: int,
        quality_scores: Optional[List[int]] = None
    ) -> int:
        """
        Calculate confidence boost based on number of angles and quality.

        Args:
            num_angles: Number of viewing angles captured
            quality_scores: Optional list of quality scores for each angle

        Returns:
            Confidence boost value (0-20)
        """
        base_boost = {
            1: 0,   # Single angle = no boost
            2: 8,   # Two angles = +8% boost
            3: 15   # Three angles = +15% boost
        }.get(num_angles, 0)

        # Adjust based on average quality if provided
        if quality_scores:
            avg_quality = np.mean(quality_scores)
            if avg_quality >= 85:
                quality_multiplier = 1.2
            elif avg_quality >= 70:
                quality_multiplier = 1.0
            else:
                quality_multiplier = 0.8

            return min(20, int(base_boost * quality_multiplier))

        return base_boost

    def detect_measurement_conflicts(
        self,
        front_measurements: Optional[Dict[str, float]] = None,
        back_measurements: Optional[Dict[str, float]] = None,
        side_measurements: Optional[Dict[str, float]] = None,
        threshold_percent: float = 20.0
    ) -> List[str]:
        """
        Detect measurements that differ significantly across angles.

        Args:
            front_measurements: Measurements from front view
            back_measurements: Measurements from back view
            side_measurements: Measurements from side view
            threshold_percent: Percentage difference threshold for conflicts

        Returns:
            List of measurement names with conflicts
        """
        conflicts = []

        # Collect measurements
        angles_data = {}
        if front_measurements:
            angles_data['front'] = front_measurements
        if back_measurements:
            angles_data['back'] = back_measurements
        if side_measurements:
            angles_data['side'] = side_measurements

        if len(angles_data) < 2:
            return conflicts

        # Check each measurement across angles
        all_keys = set()
        for measurements in angles_data.values():
            all_keys.update(measurements.keys())

        for key in all_keys:
            values = []
            for measurements in angles_data.values():
                if key in measurements:
                    values.append(measurements[key])

            if len(values) >= 2:
                min_val = min(values)
                max_val = max(values)
                if min_val > 0:
                    percent_diff = ((max_val - min_val) / min_val) * 100
                    if percent_diff > threshold_percent:
                        conflicts.append(f"{key}: {percent_diff:.1f}% difference")

        return conflicts
