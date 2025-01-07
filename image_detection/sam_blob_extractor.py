import os
import cv2
import numpy as np
import torch
from segment_anything import sam_model_registry, SamPredictor
from dataclasses import dataclass
from typing import List, Tuple, Optional
from image_detection.yolo_hold_detector import Hold

@dataclass
class BlobHold:
    """Represents a climbing hold with precise shape information."""
    center: Tuple[int, int]
    contour: np.ndarray
    area: float
    color: str
    confidence: float
    mask: np.ndarray
    convex_hull: np.ndarray
    min_rect: Tuple[Tuple[int, int], Tuple[int, int], float]  # center, size, angle

class SAMBlobExtractor:
    def __init__(self, model_path=None):
        """Initialize the SAM-based blob extractor."""
        if model_path is None:
            # Default to the model in the image_detection/model directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            model_path = os.path.join(current_dir, "model", "sam_vit_h_4b8939.pth")
        
        # Load SAM model
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        sam = sam_model_registry["vit_h"](checkpoint=model_path)
        sam.to(device=device)
        self.predictor = SamPredictor(sam)
        
        # Store device for later use
        self.device = device
    
    def _extract_hold_shape(self, image: np.ndarray, bbox: List[int]) -> Optional[np.ndarray]:
        """Extract hold shape using SAM."""
        # Convert bbox to input points and labels
        center_x = (bbox[0] + bbox[2]) // 2
        center_y = (bbox[1] + bbox[3]) // 2
        
        # Create input points
        input_point = np.array([[center_x, center_y]])
        input_label = np.array([1])  # 1 indicates foreground
        
        # Get prediction from SAM
        masks, scores, _ = self.predictor.predict(
            point_coords=input_point,
            point_labels=input_label,
            box=np.array(bbox),  # Also provide the bounding box as guidance
            multimask_output=True
        )
        
        # Get the highest scoring mask
        best_mask_idx = np.argmax(scores)
        mask = masks[best_mask_idx]
        
        # Convert mask to contour
        mask = (mask * 255).astype(np.uint8)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_L1)
        
        if not contours:
            return None
        
        # Get the largest contour
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Smooth the contour
        epsilon = 0.003 * cv2.arcLength(largest_contour, True)
        smoothed_contour = cv2.approxPolyDP(largest_contour, epsilon, True)
        
        return smoothed_contour
    
    def extract_blobs(self, image: np.ndarray, holds: List[Hold]) -> List[BlobHold]:
        """Extract precise hold shapes using SAM."""
        # Set image in predictor
        self.predictor.set_image(image)
        
        blobs = []
        for hold in holds:
            # Extract shape using SAM
            bbox = [hold.bbox[0], hold.bbox[1], hold.bbox[2], hold.bbox[3]]
            contour = self._extract_hold_shape(image, bbox)
            
            if contour is None:
                continue
            
            # Calculate properties
            hull = cv2.convexHull(contour)
            min_rect = cv2.minAreaRect(contour)
            area = cv2.contourArea(contour)
            
            # Create full image mask
            full_mask = np.zeros(image.shape[:2], dtype=np.uint8)
            cv2.drawContours(full_mask, [contour], -1, 255, -1)
            
            blobs.append(BlobHold(
                center=hold.center,
                contour=contour,
                area=area,
                color=hold.color,
                confidence=hold.confidence,
                mask=full_mask,
                convex_hull=hull,
                min_rect=min_rect
            ))
        
        return blobs
    
    def draw_blobs(self, image: np.ndarray, blobs: List[BlobHold]) -> np.ndarray:
        """Draw detected blobs on the image."""
        result = image.copy()
        
        for blob in blobs:
            # Draw contour
            cv2.drawContours(result, [blob.contour], -1, (0, 255, 0), 2)
            
            # Draw convex hull
            cv2.drawContours(result, [blob.convex_hull], -1, (255, 0, 0), 1)
            
            # Draw minimum rotated rectangle
            box = cv2.boxPoints(blob.min_rect)
            box = np.int32(box)
            cv2.drawContours(result, [box], 0, (0, 0, 255), 1)
            
            # Draw center point
            cv2.circle(result, blob.center, 3, (255, 255, 0), -1)
            
            # Add label
            label = f"{blob.color} ({blob.confidence:.2f})"
            x, y = blob.center
            cv2.putText(
                result,
                label,
                (x - 20, y - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2
            )
        
        return result
    
    def create_mask_visualization(self, image: np.ndarray, blobs: List[BlobHold]) -> np.ndarray:
        """Create a visualization of all blob masks."""
        result = image.copy()
        
        for blob in blobs:
            # Create random color for this blob
            color = np.random.randint(0, 255, 3).tolist()
            
            # Apply color to the masked region
            result[blob.mask > 0] = color
        
        return result 