"""
Test script for validating the 15 body measurements
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from measurement_estimator import MeasurementEstimator

def test_all_measurements():
    """Test that all 15 measurements are calculated"""

    # Create sample keypoints (simulating a person with 170cm height)
    # These are normalized coordinates that would come from MediaPipe
    sample_keypoints = {
        "nose": (500, 100, 0.99),
        "left_shoulder": (400, 200, 0.95),
        "right_shoulder": (600, 200, 0.95),
        "left_elbow": (350, 350, 0.90),
        "right_elbow": (650, 350, 0.90),
        "left_wrist": (320, 500, 0.85),
        "right_wrist": (680, 500, 0.85),
        "left_hip": (425, 550, 0.95),
        "right_hip": (575, 550, 0.95),
        "left_knee": (420, 800, 0.90),
        "right_knee": (580, 800, 0.90),
        "left_ankle": (415, 1050, 0.85),
        "right_ankle": (585, 1050, 0.85)
    }

    # Sample scale (pixels per cm) - for 170cm person
    # If the person's full height (nose to ankle) is ~950 pixels
    # and their height is 170cm, scale = 950 / (170 * 0.92) ≈ 6.07
    sample_scale = 6.0

    # Initialize estimator
    estimator = MeasurementEstimator()

    # Get measurements
    measurements = estimator.estimate_measurements(sample_keypoints, sample_scale)

    # Expected measurements
    expected_keys = [
        "chest", "waist", "hips", "inseam", "shoulder", "arm",  # Original 6
        "neck", "wrist", "thigh", "calf", "bicep",              # New circumferences
        "torso_length", "back_width", "rise", "ankle"           # New lengths/widths
    ]

    print("=" * 60)
    print("MEASUREMENT VALIDATION TEST")
    print("=" * 60)
    print(f"\nTotal measurements expected: {len(expected_keys)}")
    print(f"Total measurements calculated: {len(measurements)}")
    print()

    # Check all measurements are present
    all_present = True
    for key in expected_keys:
        if key in measurements:
            print(f"[OK] {key:15} = {measurements[key]:6.1f} cm")
        else:
            print(f"[FAIL] {key:15} = MISSING")
            all_present = False

    print()
    print("=" * 60)

    if all_present:
        print("[SUCCESS] All 15 measurements calculated!")
        print()
        print("Measurement Summary:")
        print("-" * 60)
        print("\nPrimary Measurements (Original 6):")
        print(f"  Chest:     {measurements['chest']} cm")
        print(f"  Waist:     {measurements['waist']} cm")
        print(f"  Hips:      {measurements['hips']} cm")
        print(f"  Shoulder:  {measurements['shoulder']} cm")
        print(f"  Arm:       {measurements['arm']} cm")
        print(f"  Inseam:    {measurements['inseam']} cm")

        print("\nCircumference Measurements (New 5):")
        print(f"  Neck:      {measurements['neck']} cm")
        print(f"  Bicep:     {measurements['bicep']} cm")
        print(f"  Wrist:     {measurements['wrist']} cm")
        print(f"  Thigh:     {measurements['thigh']} cm")
        print(f"  Calf:      {measurements['calf']} cm")
        print(f"  Ankle:     {measurements['ankle']} cm")

        print("\nLength/Width Measurements (New 3):")
        print(f"  Torso:     {measurements['torso_length']} cm")
        print(f"  Back:      {measurements['back_width']} cm")
        print(f"  Rise:      {measurements['rise']} cm")
        print()

        # Sanity checks
        print("Sanity Checks:")
        print("-" * 60)
        checks_passed = True

        # Check reasonable ranges for typical adult measurements
        if 70 <= measurements['chest'] <= 130:
            print("[OK] Chest measurement in reasonable range (70-130 cm)")
        else:
            print(f"[WARN] Chest measurement ({measurements['chest']} cm) outside typical range")
            checks_passed = False

        if 30 <= measurements['neck'] <= 50:
            print("[OK] Neck measurement in reasonable range (30-50 cm)")
        else:
            print(f"[WARN] Neck measurement ({measurements['neck']} cm) outside typical range")
            checks_passed = False

        if 10 <= measurements['wrist'] <= 25:
            print("[OK] Wrist measurement in reasonable range (10-25 cm)")
        else:
            print(f"[WARN] Wrist measurement ({measurements['wrist']} cm) outside typical range")
            checks_passed = False

        if 40 <= measurements['thigh'] <= 80:
            print("[OK] Thigh measurement in reasonable range (40-80 cm)")
        else:
            print(f"[WARN] Thigh measurement ({measurements['thigh']} cm) outside typical range")
            checks_passed = False

        if 25 <= measurements['calf'] <= 50:
            print("[OK] Calf measurement in reasonable range (25-50 cm)")
        else:
            print(f"[WARN] Calf measurement ({measurements['calf']} cm) outside typical range")
            checks_passed = False

        if 15 <= measurements['ankle'] <= 30:
            print("[OK] Ankle measurement in reasonable range (15-30 cm)")
        else:
            print(f"[WARN] Ankle measurement ({measurements['ankle']} cm) outside typical range")
            checks_passed = False

        if 35 <= measurements['torso_length'] <= 75:
            print("[OK] Torso length in reasonable range (35-75 cm)")
        else:
            print(f"[WARN] Torso length ({measurements['torso_length']} cm) outside typical range")
            checks_passed = False

        if 8 <= measurements['rise'] <= 35:
            print("[OK] Rise measurement in reasonable range (8-35 cm)")
        else:
            print(f"[WARN] Rise measurement ({measurements['rise']} cm) outside typical range")
            checks_passed = False

        print()
        if checks_passed:
            print("[SUCCESS] All sanity checks passed!")
        else:
            print("[WARN] Some measurements may need adjustment")

        return True
    else:
        print("[FAILURE] Some measurements are missing!")
        return False


if __name__ == "__main__":
    success = test_all_measurements()
    sys.exit(0 if success else 1)
