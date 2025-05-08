import cv2
import numpy as np
import os
from vision_detector import VisionDetector

def demo_vision_detector():
    """
    Demonstrate usage of the VisionDetector library
    """
    print("Vision Detector Demo")
    print("--------------------")
    
    # Create the detector
    detector = VisionDetector(keys_dir="key_images", confidence_threshold=0.7)
    
    # Make sure we have a key_images directory
    if not os.path.exists("key_images"):
        os.makedirs("key_images")
        print("Created key_images directory")
    
    # Demo with example images
    print("\n1. Creating sample key and target images...")
    
    # Create a sample key image (a simple blue rectangle)
    key_image = np.zeros((100, 100, 3), dtype=np.uint8)
    key_image[20:80, 20:80] = (255, 0, 0)  # Blue rectangle
    cv2.imwrite("key_images/blue_rectangle.png", key_image)
    
    # Add another key image (a red circle)
    circle_key = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.circle(circle_key, (50, 50), 30, (0, 0, 255), -1)  # Red circle
    cv2.imwrite("key_images/red_circle.png", circle_key)
    
    # Create a target image with both shapes
    target_image = np.zeros((500, 500, 3), dtype=np.uint8)
    
    # Add blue rectangle at position (100, 100)
    target_image[100:160, 100:160] = (255, 0, 0)
    
    # Add red circle at position (300, 300)
    cv2.circle(target_image, (300, 300), 30, (0, 0, 255), -1)
    
    # Add transformed (rotated) blue rectangle at (200, 400)
    M = cv2.getRotationMatrix2D((30, 30), 45, 1)
    rotated_rect = cv2.warpAffine(key_image, M, (100, 100))
    target_image[400:500, 200:300] = rotated_rect
    
    # Save the target image
    cv2.imwrite("target_image.png", target_image)
    
    # Reload the detector to pick up the new key images
    detector.load_key_images()
    
    print("Sample images created:")
    print("- Key images saved in 'key_images' directory")
    print("- Target image saved as 'target_image.png'")
    
    # Demo exact matching
    print("\n2. Finding exact matches...")
    
    # Load target image
    target = cv2.imread("target_image.png")
    
    # Find blue rectangle (exact match)
    result = detector.find_exact(target, "blue_rectangle")
    if result:
        print(f"Found exact match: {result}")
        
        # Draw the detection
        marked_image = detector.draw_detection(target, result)
        cv2.imwrite("result_exact.png", marked_image)
        print("- Result saved as 'result_exact.png'")
    else:
        print("No exact match found")
    
    # Find all keys
    print("\n3. Finding all key images...")
    all_results = detector.search_all_keys(target, search_type="exact")
    if all_results:
        print(f"Found {len(all_results)} matches:")
        for res in all_results:
            print(f"- {res}")
            
        # Draw all detections
        marked_image = detector.draw_all_detections(target, all_results)
        cv2.imwrite("result_all.png", marked_image)
        print("- Result saved as 'result_all.png'")
    else:
        print("No matches found")
    
    # Demo transformed matching
    print("\n4. Finding transformed matches...")
    transformed_result = detector.find_transformed(target, "blue_rectangle")
    if transformed_result:
        print(f"Found transformed match: {transformed_result}")
        
        # Draw the detection
        marked_image = detector.draw_detection(target, transformed_result)
        cv2.imwrite("result_transformed.png", marked_image)
        print("- Result saved as 'result_transformed.png'")
    else:
        print("No transformed match found")
    
    # Feature-based matching demo
    print("\n5. Finding feature-based matches...")
    feature_result = detector.find_feature_based(target, "blue_rectangle")
    if feature_result:
        print(f"Found feature-based match: {feature_result}")
        
        # Draw the detection
        marked_image = detector.draw_detection(target, feature_result)
        cv2.imwrite("result_feature.png", marked_image)
        print("- Result saved as 'result_feature.png'")
    else:
        print("No feature-based match found")
    
    # Demo with screenshot
    try:
        print("\n6. Taking screenshot and searching for keys...")
        screenshot = detector.take_screenshot()
        screenshot_results = detector.search_all_keys(screenshot)
        
        if screenshot_results:
            print(f"Found {len(screenshot_results)} matches in screenshot:")
            for res in screenshot_results:
                print(f"- {res}")
                
            # Draw detections on screenshot
            marked_screenshot = detector.draw_all_detections(screenshot, screenshot_results)
            cv2.imwrite("screenshot_results.png", marked_screenshot)
            print("- Result saved as 'screenshot_results.png'")
        else:
            print("No matches found in screenshot")
            
            # Save screenshot anyway for reference
            cv2.imwrite("screenshot.png", screenshot)
            print("- Screenshot saved as 'screenshot.png'")
    except ImportError:
        print("Screenshot demo skipped (pyautogui not installed)")
        print("Install with: pip install pyautogui")
    
    print("\nDemo completed!")

if __name__ == "__main__":
    demo_vision_detector()