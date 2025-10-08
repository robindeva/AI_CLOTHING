"""
Test client for AI Clothing Size Recommender API
"""
import requests
import json
import sys


def test_local_api(image_path: str, gender: str = "male"):
    """Test API running locally."""
    url = "http://localhost:8000/analyze"

    with open(image_path, 'rb') as f:
        files = {'image': f}
        data = {'gender': gender}

        response = requests.post(url, files=files, data=data)

    if response.status_code == 200:
        result = response.json()
        print("✓ Success!")
        print(f"\nRecommended Size: {result['recommended_size']}")
        print(f"Confidence: {result['confidence']}%")
        print(f"Explanation: {result['explanation']}")
        print(f"\nMeasurements:")
        for measurement, value in result['measurements'].items():
            print(f"  {measurement.capitalize()}: {value} cm")
        print(f"\nAll Size Scores:")
        for size, score in result['all_size_scores'].items():
            print(f"  {size}: {score:.1f}")
    else:
        print(f"✗ Error: {response.status_code}")
        print(response.text)


def test_aws_api(api_endpoint: str, image_path: str, gender: str = "male"):
    """Test API deployed on AWS."""
    url = f"{api_endpoint}/analyze"

    with open(image_path, 'rb') as f:
        files = {'image': f}
        data = {'gender': gender}

        response = requests.post(url, files=files, data=data)

    if response.status_code == 200:
        result = response.json()
        print("✓ Success!")
        print(f"\nRequest ID: {result['request_id']}")
        print(f"Recommended Size: {result['recommended_size']}")
        print(f"Confidence: {result['confidence']}%")
        print(f"Explanation: {result['explanation']}")
        print(f"\nMeasurements:")
        for measurement, value in result['measurements'].items():
            print(f"  {measurement.capitalize()}: {value} cm")
    else:
        print(f"✗ Error: {response.status_code}")
        print(response.text)


def test_custom_size_chart(image_path: str, gender: str = "male"):
    """Test API with custom size chart."""
    url = "http://localhost:8000/analyze-with-custom-chart"

    # Example custom size chart
    custom_chart = {
        "XS": {
            "chest": [81, 86],
            "waist": [66, 71],
            "hips": [86, 91],
            "inseam": [76, 79],
            "shoulder": [42, 44],
            "arm": [58, 60]
        },
        "S": {
            "chest": [86, 91],
            "waist": [71, 76],
            "hips": [91, 96],
            "inseam": [79, 81],
            "shoulder": [44, 46],
            "arm": [60, 62]
        },
        "M": {
            "chest": [91, 97],
            "waist": [76, 81],
            "hips": [96, 102],
            "inseam": [81, 84],
            "shoulder": [46, 48],
            "arm": [62, 64]
        },
        "L": {
            "chest": [97, 102],
            "waist": [81, 86],
            "hips": [102, 107],
            "inseam": [84, 86],
            "shoulder": [48, 50],
            "arm": [64, 66]
        }
    }

    with open(image_path, 'rb') as f:
        files = {'image': f}
        data = {
            'gender': gender,
            'size_chart': json.dumps(custom_chart)
        }

        response = requests.post(url, files=files, data=data)

    if response.status_code == 200:
        result = response.json()
        print("✓ Success with custom size chart!")
        print(f"\nRecommended Size: {result['recommended_size']}")
        print(f"Confidence: {result['confidence']}%")
        print(f"Explanation: {result['explanation']}")
    else:
        print(f"✗ Error: {response.status_code}")
        print(response.text)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python test_client.py <image_path> [gender] [api_endpoint]")
        print("\nExamples:")
        print("  python test_client.py photo.jpg male")
        print("  python test_client.py photo.jpg female https://xxx.execute-api.us-east-1.amazonaws.com")
        sys.exit(1)

    image_path = sys.argv[1]
    gender = sys.argv[2] if len(sys.argv) > 2 else "male"
    api_endpoint = sys.argv[3] if len(sys.argv) > 3 else None

    print(f"Testing with image: {image_path}")
    print(f"Gender: {gender}\n")

    if api_endpoint:
        print(f"Testing AWS API: {api_endpoint}")
        test_aws_api(api_endpoint, image_path, gender)
    else:
        print("Testing local API")
        test_local_api(image_path, gender)
