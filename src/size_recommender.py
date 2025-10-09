from typing import Dict, List, Tuple
from enum import Enum


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    UNISEX = "unisex"


class SizeChart:
    """Standard size charts for different genders and regions."""

    # Men's size chart (chest, waist, hips in cm)
    MENS_SIZES = {
        "XS": {"chest": (81, 86), "waist": (66, 71), "hips": (86, 91), "inseam": (76, 79), "shoulder": (42, 44), "arm": (58, 60)},
        "S": {"chest": (86, 91), "waist": (71, 76), "hips": (91, 96), "inseam": (79, 81), "shoulder": (44, 46), "arm": (60, 62)},
        "M": {"chest": (91, 97), "waist": (76, 81), "hips": (96, 102), "inseam": (81, 84), "shoulder": (46, 48), "arm": (62, 64)},
        "L": {"chest": (97, 102), "waist": (81, 86), "hips": (102, 107), "inseam": (84, 86), "shoulder": (48, 50), "arm": (64, 66)},
        "XL": {"chest": (102, 107), "waist": (86, 91), "hips": (107, 112), "inseam": (86, 89), "shoulder": (50, 52), "arm": (66, 68)},
        "XXL": {"chest": (107, 114), "waist": (91, 99), "hips": (112, 119), "inseam": (89, 91), "shoulder": (52, 54), "arm": (68, 71)},
    }

    # Women's size chart
    WOMENS_SIZES = {
        "XS": {"chest": (76, 81), "waist": (58, 63), "hips": (84, 89), "inseam": (74, 76), "shoulder": (36, 38), "arm": (56, 58)},
        "S": {"chest": (81, 86), "waist": (63, 68), "hips": (89, 94), "inseam": (76, 79), "shoulder": (38, 40), "arm": (58, 60)},
        "M": {"chest": (86, 91), "waist": (68, 73), "hips": (94, 99), "inseam": (79, 81), "shoulder": (40, 42), "arm": (60, 62)},
        "L": {"chest": (91, 99), "waist": (73, 81), "hips": (99, 107), "inseam": (81, 84), "shoulder": (42, 44), "arm": (62, 64)},
        "XL": {"chest": (99, 107), "waist": (81, 89), "hips": (107, 114), "inseam": (84, 86), "shoulder": (44, 46), "arm": (64, 66)},
        "XXL": {"chest": (107, 117), "waist": (89, 99), "hips": (114, 124), "inseam": (86, 89), "shoulder": (46, 48), "arm": (66, 69)},
    }

    @staticmethod
    def get_size_chart(gender: Gender) -> Dict:
        """Get appropriate size chart based on gender."""
        if gender == Gender.FEMALE:
            return SizeChart.WOMENS_SIZES
        elif gender == Gender.MALE:
            return SizeChart.MENS_SIZES
        else:
            # For unisex, use men's sizing
            return SizeChart.MENS_SIZES


class SizeRecommender:
    """Recommends clothing size based on body measurements."""

    def __init__(self, gender: Gender = Gender.UNISEX):
        self.gender = gender
        self.size_chart = SizeChart.get_size_chart(gender)

    def recommend_size(self, measurements: Dict[str, float]) -> Dict:
        """
        Recommend shirt size based on measurements (improved accuracy).

        Args:
            measurements: Dict with keys: chest, waist, hips, inseam, shoulder, arm

        Returns:
            Dict with recommended_size, confidence, and explanation
        """
        # Calculate fit score for each size using shirt-optimized weights
        size_scores = {}

        # Shirt-optimized weights (focus on upper body)
        shirt_weights = {
            "chest": 3.5,      # Most important for shirts
            "shoulder": 2.5,   # Critical for fit
            "arm": 1.5,        # Important for sleeve length
            "waist": 0.0,      # Not used for shirt sizing
            "hips": 0.0,       # Not used for shirt sizing
            "inseam": 0.0      # Not used for shirt sizing
        }

        for size, size_ranges in self.size_chart.items():
            score = self._calculate_fit_score_weighted(measurements, size_ranges, shirt_weights)
            size_scores[size] = score

        # Find best matching size
        best_size = max(size_scores, key=size_scores.get)
        best_score = size_scores[best_size]

        # Calculate confidence (0-100%)
        confidence = min(100, int(best_score))

        # Generate explanation
        explanation = self._generate_explanation(
            measurements, best_size, best_score, size_scores
        )

        return {
            "recommended_size": best_size,
            "confidence": confidence,
            "explanation": explanation,
            "measurements": measurements,
            "all_size_scores": size_scores
        }

    def _calculate_fit_score_weighted(self, measurements: Dict[str, float], size_ranges: Dict, weights: Dict[str, float]) -> float:
        """
        Calculate how well measurements fit a given size with custom weights.
        Returns score 0-100 (higher is better).
        """
        scores = []

        for measurement_name, value in measurements.items():
            if measurement_name not in size_ranges or measurement_name not in weights:
                continue

            weight = weights[measurement_name]
            if weight == 0:  # Skip measurements with zero weight
                continue

            min_val, max_val = size_ranges[measurement_name]

            # Check if measurement falls within range
            if min_val <= value <= max_val:
                # Perfect fit - center of range gets 100
                range_center = (min_val + max_val) / 2
                range_width = max_val - min_val
                deviation = abs(value - range_center)
                score = 100 * (1 - deviation / (range_width / 2))
            else:
                # Outside range - penalize based on distance
                if value < min_val:
                    distance = min_val - value
                else:
                    distance = value - max_val

                # Reduce score based on distance (cm)
                score = max(0, 100 - (distance * 10))

            scores.append(score * weight)

        # Weighted average
        total_weight = sum(w for w in weights.values() if w > 0)
        final_score = sum(scores) / total_weight if scores and total_weight > 0 else 0

        return final_score

    def _calculate_fit_score(self, measurements: Dict[str, float], size_ranges: Dict) -> float:
        """
        Calculate how well measurements fit a given size.
        Returns score 0-100 (higher is better).
        """
        scores = []
        weights = {
            "chest": 2.0,    # Most important
            "waist": 1.8,
            "hips": 1.5,
            "inseam": 1.0,
            "shoulder": 1.2,
            "arm": 0.8
        }

        for measurement_name, value in measurements.items():
            if measurement_name not in size_ranges:
                continue

            min_val, max_val = size_ranges[measurement_name]
            weight = weights.get(measurement_name, 1.0)

            # Check if measurement falls within range
            if min_val <= value <= max_val:
                # Perfect fit - center of range gets 100
                range_center = (min_val + max_val) / 2
                range_width = max_val - min_val
                deviation = abs(value - range_center)
                score = 100 * (1 - deviation / (range_width / 2))
            else:
                # Outside range - penalize based on distance
                if value < min_val:
                    distance = min_val - value
                else:
                    distance = value - max_val

                # Reduce score based on distance (cm)
                score = max(0, 100 - (distance * 10))

            scores.append(score * weight)

        # Weighted average
        total_weight = sum(weights.values())
        final_score = sum(scores) / total_weight if scores else 0

        return final_score

    def _generate_explanation(
        self,
        measurements: Dict[str, float],
        recommended_size: str,
        score: float,
        all_scores: Dict
    ) -> str:
        """Generate human-readable explanation for the recommendation."""

        size_ranges = self.size_chart[recommended_size]

        # Check which measurements are out of range
        tight_measurements = []
        loose_measurements = []

        for measurement_name, value in measurements.items():
            if measurement_name not in size_ranges:
                continue

            min_val, max_val = size_ranges[measurement_name]

            if value < min_val:
                loose_measurements.append(measurement_name)
            elif value > max_val:
                tight_measurements.append(measurement_name)

        # Build explanation with "Shirt Size" label
        if score >= 90:
            explanation = f"Shirt Size: {recommended_size}. Excellent fit - matches your chest ({measurements['chest']:.1f}cm) and shoulders ({measurements['shoulder']:.1f}cm) closely."
        elif score >= 75:
            explanation = f"Shirt Size: {recommended_size}. Good fit for your chest ({measurements['chest']:.1f}cm) and shoulders ({measurements['shoulder']:.1f}cm)."
        elif score >= 60:
            explanation = f"Shirt Size: {recommended_size} recommended, but fit may vary by brand."
        else:
            explanation = f"Shirt Size: {recommended_size} is the closest match. Consider trying adjacent sizes."

        # Add specific notes
        if tight_measurements:
            explanation += f" May be slightly snug in {', '.join(tight_measurements)}."
        if loose_measurements:
            explanation += f" May be slightly loose in {', '.join(loose_measurements)}."

        return explanation

    def set_custom_size_chart(self, custom_chart: Dict):
        """Allow stores to provide their own size charts."""
        self.size_chart = custom_chart
