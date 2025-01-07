import os
import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple
from ultralytics import YOLO

@dataclass
class Hold:
    center: Tuple[int, int]
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    confidence: float
    color: str = "unknown"

class YOLOHoldDetector:
    def __init__(self, model_path: str = None, confidence_threshold: float = 0.25, nms_iou_threshold: float = 0.45):
        if model_path is None:
            # Try to find the trained model in the model directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            model_path = os.path.join(current_dir, "model", "best.pt")
            
            # If not found, fall back to pre-trained model
            if not os.path.exists(model_path):
                print("Warning: Trained model not found, using pre-trained YOLOv8n")
                self.model = YOLO('yolov8n.pt')
            else:
                print(f"Using trained model from: {model_path}")
                self.model = YOLO(model_path)
        else:
            self.model = YOLO(model_path)
        
        self.confidence_threshold = confidence_threshold
        self.nms_iou_threshold = nms_iou_threshold
        
        # Color ranges in HSV
        self.color_ranges = {
            "yellow": ((20, 100, 100), (40, 255, 255)),
            "blue": ((100, 100, 100), (140, 255, 255)),
            "gray": ((0, 0, 50), (180, 30, 200))
        }
    
    def detect_holds(self, image: np.ndarray) -> List[Hold]:
        """Detect holds in the image using YOLO model."""
        results = self.model(image, verbose=False)[0]
        holds = []
        
        for box in results.boxes:
            confidence = float(box.conf[0])
            if confidence < self.confidence_threshold:
                continue
                
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            
            # Calculate center
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            
            # Get color of the hold
            hold_region = image[y1:y2, x1:x2]
            color = self._classify_color(hold_region)
            
            holds.append(Hold(
                center=(center_x, center_y),
                bbox=(x1, y1, x2, y2),
                confidence=confidence,
                color=color
            ))
        
        # Apply NMS to remove overlapping detections
        holds = self._apply_nms(holds)
        
        return holds
    
    def _classify_color(self, image: np.ndarray) -> str:
        """Classify the color of a hold based on its HSV values."""
        if image.size == 0:
            return "unknown"
        
        # Convert to HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Calculate average HSV values
        avg_hsv = np.mean(hsv, axis=(0, 1))
        
        # Check each color range
        for color, (lower, upper) in self.color_ranges.items():
            lower = np.array(lower)
            upper = np.array(upper)
            
            if np.all(avg_hsv >= lower) and np.all(avg_hsv <= upper):
                return color
        
        return "unknown"
    
    def draw_holds(self, image: np.ndarray, holds: List[Hold]) -> np.ndarray:
        """Draw detected holds on the image."""
        result = image.copy()
        
        color_map = {
            "yellow": (0, 255, 255),
            "blue": (255, 0, 0),
            "gray": (128, 128, 128),
            "unknown": (0, 255, 0)
        }
        
        for hold in holds:
            x1, y1, x2, y2 = hold.bbox
            color = color_map.get(hold.color, (0, 255, 0))
            
            # Draw bounding box
            cv2.rectangle(result, (x1, y1), (x2, y2), color, 2)
            
            # Draw center point
            cv2.circle(result, hold.center, 3, color, -1)
            
            # Draw confidence score
            text = f"{hold.color} ({hold.confidence:.2f})"
            cv2.putText(result, text, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        return result 
    
    def _apply_nms(self, holds: List[Hold]) -> List[Hold]:
        """Apply Non-Maximum Suppression to remove overlapping detections."""
        if not holds:
            return holds
            
        # Convert holds to numpy arrays for easier processing
        boxes = np.array([[h.bbox[0], h.bbox[1], h.bbox[2], h.bbox[3]] for h in holds])
        scores = np.array([h.confidence for h in holds])
        
        # Calculate areas
        areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
        
        # Sort by confidence
        order = scores.argsort()[::-1]
        
        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            
            if order.size == 1:
                break
                
            # Calculate IoU with rest of boxes
            xx1 = np.maximum(boxes[i, 0], boxes[order[1:], 0])
            yy1 = np.maximum(boxes[i, 1], boxes[order[1:], 1])
            xx2 = np.minimum(boxes[i, 2], boxes[order[1:], 2])
            yy2 = np.minimum(boxes[i, 3], boxes[order[1:], 3])
            
            w = np.maximum(0.0, xx2 - xx1)
            h = np.maximum(0.0, yy2 - yy1)
            inter = w * h
            
            ovr = inter / (areas[i] + areas[order[1:]] - inter)
            
            inds = np.where(ovr <= self.nms_iou_threshold)[0]
            order = order[inds + 1]
        
        return [holds[i] for i in keep] 