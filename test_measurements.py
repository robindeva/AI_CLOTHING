"""
Test script to validate measurement accuracy improvements.
Compares system output against known real measurements.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from pose_detector import BodyKeypointDetector
from measurement_estimator import MeasurementEstimator


def test_with_image(image_path: str, height_cm: int, real_measurements: dict):
    """
    Test measurement accuracy with a real image and known measurements.

    Args:
        image_path: Path to the test image
        height_cm: User's actual height in cm
        real_measurements: Dictionary of actual measurements
    """
    print("=" * 70)
    print("MEASUREMENT ACCURACY TEST")
    print("=" * 70)
    print(f"\nTest Image: {image_path}")
    print(f"User Height: {height_cm} cm")
    print()

    # Load image
    with open(image_path, 'rb') as f:
        image_bytes = f.read()

    # Initialize components
    detector = BodyKeypointDetector()
    estimator = MeasurementEstimator()

    # Process image
    print("Processing image and detecting pose...")
    detection_result = detector.process_image(image_bytes, height_cm)
    print(f"✓ Pose detected successfully")
    print(f"  Scale: {detection_result['scale']:.2f} pixels/cm")
    print()

    # Estimate measurements (without calibration)
    print("Estimating measurements (uncalibrated)...")
    uncalibrated_measurements = estimator.estimate_measurements(
        detection_result["keypoints"],
        detection_result["scale"],
        apply_calibration=False
    )

    # Display comparison
    print("\n" + "-" * 70)
    print(f"{'Measurement':<15} {'Real (cm)':<12} {'Output (cm)':<12} {'Error':<12} {'Error %'}")
    print("-" * 70)

    total_error = 0
    count = 0

    for measure_name, real_value in real_measurements.items():
        output_value = uncalibrated_measurements.get(measure_name, 0)
        error = output_value - real_value
        error_pct = (error / real_value * 100) if real_value > 0 else 0

        status = "✓" if abs(error_pct) < 10 else "✗"

        print(f"{measure_name.capitalize():<15} {real_value:<12.1f} {output_value:<12.1f} "
              f"{error:+7.1f} cm   {error_pct:+6.1f}% {status}")

        total_error += abs(error_pct)
        count += 1

    avg_error = total_error / count if count > 0 else 0

    print("-" * 70)
    print(f"Average Absolute Error: {avg_error:.1f}%")
    print()

    # Test calibration system
    print("\n" + "=" * 70)
    print("TESTING CALIBRATION SYSTEM")
    print("=" * 70)
    print("\nCalibrating with known measurements...")

    estimator.calibrate(
        detection_result["keypoints"],
        detection_result["scale"],
        real_measurements
    )

    print("Calibration factors:")
    for measure_name, factor in estimator.calibration_factors.items():
        if measure_name in real_measurements:
            print(f"  {measure_name.capitalize()}: {factor:.3f}x")

    # Re-estimate with calibration
    print("\nEstimating measurements (calibrated)...")
    calibrated_measurements = estimator.estimate_measurements(
        detection_result["keypoints"],
        detection_result["scale"],
        apply_calibration=True
    )

    print("\n" + "-" * 70)
    print(f"{'Measurement':<15} {'Real (cm)':<12} {'Calibrated (cm)':<15} {'Error'}")
    print("-" * 70)

    total_calibrated_error = 0

    for measure_name, real_value in real_measurements.items():
        calibrated_value = calibrated_measurements.get(measure_name, 0)
        error = calibrated_value - real_value
        error_pct = (error / real_value * 100) if real_value > 0 else 0

        status = "✓" if abs(error_pct) < 2 else "~"

        print(f"{measure_name.capitalize():<15} {real_value:<12.1f} {calibrated_value:<15.1f} "
              f"{error:+7.1f} cm {status}")

        total_calibrated_error += abs(error_pct)

    avg_calibrated_error = total_calibrated_error / count if count > 0 else 0

    print("-" * 70)
    print(f"Average Absolute Error (Calibrated): {avg_calibrated_error:.1f}%")
    print()

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    improvement = avg_error - avg_calibrated_error
    print(f"Before improvements: {avg_error:.1f}% average error")
    print(f"After improvements:  {avg_calibrated_error:.1f}% average error")
    print(f"Improvement:         {improvement:.1f}% reduction in error")
    print()

    if avg_error < 15:
        print("✓ Measurements are reasonably accurate!")
    else:
        print("⚠ Measurements need further tuning.")

    print("=" * 70)


if __name__ == "__main__":
    # Your real measurements
    real_measurements = {
        "shoulder": 44,
        "waist": 58,
        "hips": 65,
        "inseam": 71,
        "chest": 83,
        "arm": 56
    }

    # Test with your image
    # Replace with the actual path to your test image
    image_path = input("\nEnter path to your test image: ").strip()

    if not Path(image_path).exists():
        print(f"Error: Image not found at {image_path}")
        print("\nPlease provide the full path to your test image.")
        sys.exit(1)

    test_with_image(image_path, 172, real_measurements)
