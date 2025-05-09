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
    
    # Reload the detector to pick up the new key images
    detector.load_key_images()
        
    # Load target image
    target = cv2.imread("target.png")
    
    # Find all keys
    print("\n3. Finding all key images...")
    all_results = detector.search_all_keys(target, search_type="feature_based")
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
            
    print("\nDemo completed!")

if __name__ == "__main__":
    demo_vision_detector()