import os
import cv2
import numpy as np
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Union, Literal

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('VisionDetector')

@dataclass
class DetectionResult:
    """Class to store detection results"""
    key_name: str
    confidence: float
    location: Tuple[int, int]  # Top-left corner (x, y)
    size: Tuple[int, int]  # Width and height
    match_type: str
    
    @property
    def center(self) -> Tuple[int, int]:
        """Get the center point of the detection"""
        x, y = self.location
        w, h = self.size
        return (x + w // 2, y + h // 2)
    
    @property
    def box(self) -> Tuple[int, int, int, int]:
        """Get the bounding box as (x, y, width, height)"""
        x, y = self.location
        w, h = self.size
        return (x, y, w, h)
    
    @property
    def box_points(self) -> Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int], Tuple[int, int]]:
        """Get the four corners of the bounding box"""
        x, y = self.location
        w, h = self.size
        return ((x, y), (x + w, y), (x + w, y + h), (x, y + h))
    
    def __str__(self) -> str:
        return (f"Found '{self.key_name}' with {self.confidence:.2f} confidence at "
                f"position {self.location}, size {self.size}, match type: {self.match_type}")


class VisionDetector:
    """Main class for vision-based detection"""
    
    def __init__(self, keys_dir: str = "key_images", 
                 confidence_threshold: float = 0.8):
        """
        Initialize the vision detector
        
        Args:
            keys_dir: Directory containing key images
            confidence_threshold: Minimum confidence threshold for matches (0.0-1.0)
        """
        self.keys_dir = keys_dir
        self.confidence_threshold = confidence_threshold
        self.key_images: Dict[str, np.ndarray] = {}
        self.load_key_images()
        
    def load_key_images(self) -> None:
        """Load all key images from the keys directory"""
        if not os.path.exists(self.keys_dir):
            logger.warning(f"Key images directory '{self.keys_dir}' not found")
            return
            
        logger.info(f"Loading key images from {self.keys_dir}")
        
        for filename in os.listdir(self.keys_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                file_path = os.path.join(self.keys_dir, filename)
                try:
                    # Read image in both color and grayscale for different search methods
                    img = cv2.imread(file_path)
                    if img is None:
                        logger.warning(f"Failed to load image: {file_path}")
                        continue
                        
                    key_name = os.path.splitext(filename)[0]
                    self.key_images[key_name] = img
                    logger.info(f"Loaded key image: {key_name} ({img.shape[1]}x{img.shape[0]})")
                except Exception as e:
                    logger.error(f"Error loading image {file_path}: {e}")
        
        logger.info(f"Loaded {len(self.key_images)} key images")
    
    def add_key_image(self, key_name: str, image: np.ndarray) -> bool:
        """
        Add a key image programmatically
        
        Args:
            key_name: Name for the key image
            image: Image data as numpy array
            
        Returns:
            True if successful
        """
        if key_name in self.key_images:
            logger.warning(f"Key image '{key_name}' already exists, overwriting")
            
        self.key_images[key_name] = image
        logger.info(f"Added key image: {key_name} ({image.shape[1]}x{image.shape[0]})")
        return True
    
    def save_key_image(self, key_name: str, image: np.ndarray) -> bool:
        """
        Save a key image to the keys directory
        
        Args:
            key_name: Name for the key image
            image: Image data as numpy array
            
        Returns:
            True if successful
        """
        if not os.path.exists(self.keys_dir):
            os.makedirs(self.keys_dir)
            
        file_path = os.path.join(self.keys_dir, f"{key_name}.png")
        try:
            cv2.imwrite(file_path, image)
            self.key_images[key_name] = image
            logger.info(f"Saved key image: {key_name} to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving image {file_path}: {e}")
            return False
    
    def _prepare_images(self, image: np.ndarray, key_image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Convert images to grayscale for template matching"""
        if len(image.shape) == 3:
            gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray_image = image
            
        if len(key_image.shape) == 3:
            gray_key = cv2.cvtColor(key_image, cv2.COLOR_BGR2GRAY)
        else:
            gray_key = key_image
            
        return gray_image, gray_key
    
    def find_exact(self, image: np.ndarray, key_name: str) -> Optional[DetectionResult]:
        """
        Find an exact match of a key image in the target image
        
        Args:
            image: Target image to search in
            key_name: Name of the key image to find
            
        Returns:
            DetectionResult or None if not found
        """
        if key_name not in self.key_images:
            logger.warning(f"Key image '{key_name}' not found")
            return None
            
        key_image = self.key_images[key_name]
        gray_image, gray_key = self._prepare_images(image, key_image)
        
        # Perform template matching
        result = cv2.matchTemplate(gray_image, gray_key, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        # Use max_val as confidence and check threshold
        if max_val < self.confidence_threshold:
            return None
            
        # Get location of the match
        top_left = max_loc
        h, w = gray_key.shape
        
        return DetectionResult(
            key_name=key_name,
            confidence=float(max_val),
            location=(top_left[0], top_left[1]),
            size=(w, h),
            match_type="exact"
        )
    
    def find_all_exact(self, image: np.ndarray, key_name: str, 
                       max_results: int = 10) -> List[DetectionResult]:
        """
        Find all exact matches of a key image in the target image
        
        Args:
            image: Target image to search in
            key_name: Name of the key image to find
            max_results: Maximum number of results to return
            
        Returns:
            List of DetectionResults
        """
        if key_name not in self.key_images:
            logger.warning(f"Key image '{key_name}' not found")
            return []
            
        key_image = self.key_images[key_name]
        gray_image, gray_key = self._prepare_images(image, key_image)
        
        # Perform template matching
        result = cv2.matchTemplate(gray_image, gray_key, cv2.TM_CCOEFF_NORMED)
        h, w = gray_key.shape
        
        # Find all locations above threshold
        locations = np.where(result >= self.confidence_threshold)
        results = []
        
        # Convert to list of points and group nearby detections
        points = list(zip(*locations[::-1]))  # Convert to (x, y) format
        
        # Sort by confidence (highest first)
        confidences = [result[y, x] for x, y in points]
        sorted_indices = np.argsort(confidences)[::-1]
        
        # Filter points within distance of each other
        filtered_points = []
        for idx in sorted_indices:
            x, y = points[idx]
            confidence = confidences[idx]
            
            # Skip if too close to an already detected point
            too_close = False
            for fx, fy in filtered_points:
                if abs(fx - x) < w // 2 and abs(fy - y) < h // 2:
                    too_close = True
                    break
                    
            if not too_close:
                filtered_points.append((x, y))
                results.append(
                    DetectionResult(
                        key_name=key_name,
                        confidence=float(confidence),
                        location=(x, y),
                        size=(w, h),
                        match_type="exact"
                    )
                )
                
            # Check if we have enough results
            if len(results) >= max_results:
                break
                
        return results
    
    def find_transformed(self, image: np.ndarray, key_name: str, 
                        scale_range: Tuple[float, float] = (0.5, 1.5),
                        rotation_range: Tuple[int, int] = (-30, 30),
                        rotation_step: int = 10) -> Optional[DetectionResult]:
        """
        Find a transformed (scaled/rotated) match of a key image
        
        Args:
            image: Target image to search in
            key_name: Name of the key image to find
            scale_range: Tuple of (min_scale, max_scale) to search
            rotation_range: Tuple of (min_angle, max_angle) to search in degrees
            rotation_step: Step size for rotation search in degrees
            
        Returns:
            DetectionResult or None if not found
        """
        if key_name not in self.key_images:
            logger.warning(f"Key image '{key_name}' not found")
            return None
            
        key_image = self.key_images[key_name]
        gray_image, gray_key = self._prepare_images(image, key_image)
        
        best_result = None
        best_confidence = 0.0
        
        min_scale, max_scale = scale_range
        min_angle, max_angle = rotation_range
        h, w = gray_key.shape
        
        # Search through scales and rotations
        for scale in np.linspace(min_scale, max_scale, 5):
            new_w, new_h = int(w * scale), int(h * scale)
            if new_w <= 0 or new_h <= 0:
                continue
                
            # Resize the key image
            resized_key = cv2.resize(gray_key, (new_w, new_h))
            
            for angle in range(min_angle, max_angle + 1, rotation_step):
                if angle == 0 and scale == 1.0:
                    # Skip identity transform, it's handled by find_exact
                    continue
                    
                # Rotate the key image
                M = cv2.getRotationMatrix2D((new_w // 2, new_h // 2), angle, 1)
                rotated_key = cv2.warpAffine(resized_key, M, (new_w, new_h))
                
                # Search for the rotated key image
                result = cv2.matchTemplate(gray_image, rotated_key, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                
                if max_val > best_confidence:
                    best_confidence = max_val
                    best_result = DetectionResult(
                        key_name=key_name,
                        confidence=float(max_val),
                        location=(max_loc[0], max_loc[1]),
                        size=(new_w, new_h),
                        match_type=f"transformed(scale={scale:.2f},rotation={angle})"
                    )
        
        return best_result if best_confidence >= self.confidence_threshold else None
    
    def find_feature_based(self, image: np.ndarray, key_name: str,
                          min_matches: int = 10) -> Optional[DetectionResult]:
        """
        Find a key image using feature matching (handles occlusion, perspective)
        
        Args:
            image: Target image to search in
            key_name: Name of the key image to find
            min_matches: Minimum number of feature matches required
            
        Returns:
            DetectionResult or None if not found
        """
        if key_name not in self.key_images:
            logger.warning(f"Key image '{key_name}' not found")
            return None
            
        key_image = self.key_images[key_name]
        
        # Initialize SIFT detector
        sift = cv2.SIFT_create()
        
        # Find keypoints and descriptors
        kp1, des1 = sift.detectAndCompute(key_image, None)
        kp2, des2 = sift.detectAndCompute(image, None)
        
        if des1 is None or des2 is None or len(kp1) < 2 or len(kp2) < 2:
            return None
        
        # FLANN parameters and matcher
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        flann = cv2.FlannBasedMatcher(index_params, search_params)
        
        matches = flann.knnMatch(des1, des2, k=2)
        
        # Apply ratio test to filter good matches
        good_matches = []
        for m, n in matches:
            if m.distance < 0.7 * n.distance:
                good_matches.append(m)
        
        if len(good_matches) < min_matches:
            return None
            
        # Calculate confidence based on number of good matches
        confidence = min(1.0, len(good_matches) / min_matches)
        
        # Extract location from matches
        src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        
        # Find homography
        H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        
        if H is None:
            return None
            
        # Get the corners of the key image
        h, w = key_image.shape[:2]
        corners = np.float32([[0, 0], [0, h-1], [w-1, h-1], [w-1, 0]]).reshape(-1, 1, 2)
        
        # Transform corners to get bounding box in target image
        transformed_corners = cv2.perspectiveTransform(corners, H)
        
        # Calculate bounding box
        x_min = int(min(transformed_corners[0][0][0], transformed_corners[1][0][0], 
                     transformed_corners[2][0][0], transformed_corners[3][0][0]))
        y_min = int(min(transformed_corners[0][0][1], transformed_corners[1][0][1], 
                     transformed_corners[2][0][1], transformed_corners[3][0][1]))
        x_max = int(max(transformed_corners[0][0][0], transformed_corners[1][0][0], 
                     transformed_corners[2][0][0], transformed_corners[3][0][0]))
        y_max = int(max(transformed_corners[0][0][1], transformed_corners[1][0][1], 
                     transformed_corners[2][0][1], transformed_corners[3][0][1]))
        
        box_width = x_max - x_min
        box_height = y_max - y_min
        
        return DetectionResult(
            key_name=key_name,
            confidence=float(confidence),
            location=(x_min, y_min),
            size=(box_width, box_height),
            match_type="feature_based"
        )
    
    def search_all_keys(self, image: np.ndarray, 
                       search_type: Literal["exact", "transformed", "feature_based"] = "exact") -> List[DetectionResult]:
        """
        Search for all loaded key images in the target image
        
        Args:
            image: Target image to search in
            search_type: Type of search to perform
            
        Returns:
            List of DetectionResults
        """
        results = []
        
        for key_name in self.key_images:
            result = None
            
            if search_type == "exact":
                result = self.find_exact(image, key_name)
            elif search_type == "transformed":
                result = self.find_transformed(image, key_name)
            elif search_type == "feature_based":
                result = self.find_feature_based(image, key_name)
                
            if result:
                results.append(result)
                
        # Sort by confidence
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results
    
    def take_screenshot(self) -> np.ndarray:
        """
        Take a screenshot of the entire screen
        
        Returns:
            Screenshot as numpy array
        """
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        except ImportError:
            logger.error("pyautogui is required for taking screenshots")
            raise ImportError("pyautogui is required for taking screenshots")
    
    def draw_detection(self, image: np.ndarray, detection: DetectionResult, 
                      color: Tuple[int, int, int] = (0, 255, 0),
                      thickness: int = 2) -> np.ndarray:
        """
        Draw a detection result on an image
        
        Args:
            image: Image to draw on
            detection: DetectionResult to visualize
            color: BGR color tuple
            thickness: Line thickness
            
        Returns:
            Image with detection drawn
        """
        result = image.copy()
        
        # Draw rectangle
        x, y = detection.location
        w, h = detection.size
        cv2.rectangle(result, (x, y), (x + w, y + h), color, thickness)
        
        # Draw label with confidence
        label = f"{detection.key_name}: {detection.confidence:.2f}"
        font_scale = 0.5
        (text_width, text_height), baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1
        )
        
        # Draw text background
        cv2.rectangle(
            result, 
            (x, y - text_height - 5), 
            (x + text_width, y), 
            color, 
            -1
        )
        
        # Draw text
        cv2.putText(
            result,
            label,
            (x, y - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (0, 0, 0),
            1
        )
        
        return result
    
    def draw_all_detections(self, image: np.ndarray, detections: List[DetectionResult]) -> np.ndarray:
        """
        Draw multiple detection results on an image
        
        Args:
            image: Image to draw on
            detections: List of DetectionResults to visualize
            
        Returns:
            Image with all detections drawn
        """
        result = image.copy()
        
        # Generate different colors for each detection
        colors = [
            (0, 255, 0),    # Green
            (255, 0, 0),    # Blue
            (0, 0, 255),    # Red
            (255, 255, 0),  # Cyan
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Yellow
        ]
        
        for i, detection in enumerate(detections):
            color = colors[i % len(colors)]
            result = self.draw_detection(result, detection, color)
            
        return result