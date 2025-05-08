# Vision Detector Library

A Python library for detecting key images within screenshots or other images. This library can be used as a component in automation scripts, game bots, UI testing, and other applications requiring visual recognition.

## Features

- Load key images from a directory
- Search for key images within screenshots or other images
- Multiple search modes:
  - Exact matching
  - Transformed matching (rotation, scaling)
  - Feature-based matching (handles occlusion, perspective changes)
- Find single or multiple matches
- Capture screenshots
- Visualize detection results

## Requirements

- Python 3.6+
- OpenCV (cv2)
- NumPy
- PyAutoGUI (optional, for screenshot functionality)

## Installation

1. Install the required packages:

```bash
pip install opencv-python numpy
pip install pyautogui  # Optional, for screenshot functionality
```

2. Copy the `vision_detector.py` file to your project directory.

## Usage

### Basic Usage

```python
from vision_detector import VisionDetector

# Initialize the detector
detector = VisionDetector(keys_dir="key_images", confidence_threshold=0.7)

# Take a screenshot
screenshot = detector.take_screenshot()

# Find a specific key image
result = detector.find_exact(screenshot, "button_ok")
if result:
    print(f"Found '{result.key_name}' at {result.location}")
    
    # Get the center coordinates (useful for clicking)
    center_x, center_y = result.center
    print(f"Center point: ({center_x}, {center_y})")
```

### Finding Multiple Matches

```python
# Find all instances of a key image
results = detector.find_all_exact(screenshot, "icon_star", max_results=5)
for result in results:
    print(f"Found '{result.key_name}' at {result.location} with confidence {result.confidence:.2f}")
```

### Finding Transformed Matches

```python
# Find a rotated or scaled key image
result = detector.find_transformed(
    screenshot, 
    "logo", 
    scale_range=(0.5, 2.0),
    rotation_range=(-45, 45)
)
```

### Feature-Based Matching

```python
# Find a key image that might be partially occluded or perspective-transformed
result = detector.find_feature_based(screenshot, "complex_image")
```

### Visualizing Results

```python
# Draw detection results on an image
if result:
    marked_image = detector.draw_detection(screenshot, result)
    cv2.imwrite("result.png", marked_image)
```

### Searching for All Key Images

```python
# Find all loaded key images in the screenshot
all_results = detector.search_all_keys(screenshot, search_type="exact")
marked_image = detector.draw_all_detections(screenshot, all_results