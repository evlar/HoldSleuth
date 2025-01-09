import os
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import cv2
import numpy as np
from image_detection.yolo_hold_detector import YOLOHoldDetector, Hold
from image_detection.sam_blob_extractor import SAMBlobExtractor
from image_detection.SVG_to_image_grid import convert_svg_to_jpeg_grid

def get_initial_detections(image_path):
    """
    Get initial YOLO detections for review.
    
    Args:
        image_path (str): Path to the uploaded image file
        
    Returns:
        tuple: (detection_image_path, holds) - path to the image with initial detections and list of detected holds
    """
    try:
        # Load and preprocess image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Failed to load image: {image_path}")
        
        # Enhance contrast using CLAHE
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(4, 4))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        image = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        
        # Initialize YOLO detector
        yolo_detector = YOLOHoldDetector(
            confidence_threshold=0.25,
            nms_iou_threshold=0.4
        )
        
        # Detect holds using YOLO
        holds = yolo_detector.detect_holds(image)
        
        # Draw initial detections
        detection_image = yolo_detector.draw_holds(image, holds)
        
        # Save detection image for review
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        detection_path = os.path.join('static', 'uploads', f"{base_name}_detections.jpg")
        cv2.imwrite(detection_path, detection_image)
        
        # Convert holds to a format suitable for JSON
        holds_data = []
        for hold in holds:
            holds_data.append({
                'center': [int(hold.center[0]), int(hold.center[1])],
                'bbox': [int(x) for x in hold.bbox],
                'confidence': float(hold.confidence),
                'color': hold.color
            })
        
        return detection_path, holds_data
        
    except Exception as e:
        raise Exception(f"Error getting initial detections: {str(e)}")

def process_final_holds(image_path, approved_holds):
    """
    Process the final approved holds to create grid-aligned outputs.
    
    Args:
        image_path (str): Path to the uploaded image file
        approved_holds: List of holds after user review
        
    Returns:
        tuple: (svg_path, grid_jpg_path) - paths to the generated SVG and JPEG files
    """
    try:
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Failed to load image: {image_path}")
        
        # Convert approved holds back to Hold objects
        holds = []
        for hold_data in approved_holds:
            # Handle both t-nuts (with center) and boxes (with just bbox)
            if 'center' in hold_data:
                # T-nut point
                holds.append(Hold(
                    center=tuple(hold_data['center']),
                    bbox=tuple(hold_data['bbox']),
                    confidence=float(hold_data['confidence']),
                    color=hold_data['color']
                ))
            else:
                # Box only
                x1, y1, x2, y2 = hold_data['bbox']
                center = ((x1 + x2) / 2, (y1 + y2) / 2)
                holds.append(Hold(
                    center=center,
                    bbox=tuple(hold_data['bbox']),
                    confidence=float(hold_data['confidence']),
                    color=hold_data['color']
                ))
        
        # Initialize SAM blob extractor
        blob_extractor = SAMBlobExtractor()
        
        # Extract precise shapes using SAM
        blobs = blob_extractor.extract_blobs(image, holds)
        
        # Get paths for grid processing
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # Temporary SVG path for intermediate processing
        temp_svg = os.path.join(project_root, 'output', 'svg', f"{base_name}.svg")
        
        # Final output paths
        output_jpg = os.path.join(project_root, 'output', 'grid', f"converted_grid_{base_name}.jpg")
        output_svg = os.path.join(project_root, 'output', 'svg', 'grid', f"{base_name}_grid.svg")
        
        # Create SVG with approved holds
        save_as_svg(blobs, temp_svg)
        
        # Convert to grid-aligned outputs
        convert_svg_to_jpeg_grid(temp_svg, output_jpg, output_svg, debug=False)
        
        # Clean up temporary files
        if os.path.exists(temp_svg):
            os.remove(temp_svg)
            
        # Convert paths to be relative to web interface root
        svg_path = os.path.relpath(output_svg, start=os.path.dirname(os.path.dirname(__file__)))
        grid_jpg_path = os.path.relpath(output_jpg, start=os.path.dirname(os.path.dirname(__file__)))
            
        return svg_path, grid_jpg_path
        
    except Exception as e:
        raise Exception(f"Error processing final holds: {str(e)}")

def save_as_svg(blobs, output_path):
    """Save the detected holds as an SVG file."""
    try:
        # Get image dimensions from first blob's mask
        if blobs and blobs[0].mask is not None:
            height, width = blobs[0].mask.shape
        else:
            width, height = 1920, 1080  # Default dimensions if no blobs
        
        # Create SVG content manually
        svg_content = [
            '<?xml version="1.0" encoding="utf-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}px" height="{height}px" viewBox="0 0 {width} {height}">',
            '<g>'  # Root group
        ]
        
        # Calculate grid parameters
        grid_width = width / 8  # 8 columns
        grid_height = height / 40  # 40 rows
        
        # Add holds to the SVG
        for blob in blobs:
            try:
                # Ensure contour is properly shaped
                if blob.contour is None or len(blob.contour) < 3:
                    print(f"Skipping invalid contour for blob at {blob.center}")
                    continue
                
                # Convert contour points to SVG polygon points
                contour = blob.contour.reshape(-1, 2)
                points = []
                for x, y in contour:
                    points.append(f"{float(x)},{float(y)}")
                points_str = " ".join(points)
                
                # Calculate grid position
                grid_x = int(min(7, max(0, blob.center[0] / grid_width)))
                grid_y = int(max(0, blob.center[1] / grid_height))
                
                # Create polygon with hold color and metadata
                color = blob.color if blob.color != "unknown" else "#808080"
                tnut_x = float(blob.center[0])
                tnut_y = float(blob.center[1])
                
                polygon = (
                    f'<polygon points="{points_str}" '
                    f'fill="{color}" '
                    f'stroke="#000000" '
                    f'stroke-width="1" '
                    f'opacity="0.5" '
                    f'data-grid-x="{grid_x}" '
                    f'data-grid-y="{grid_y}" '
                    f'data-grid-position="{grid_x},{grid_y}" '
                    f'data-tnut-x="{tnut_x}" '
                    f'data-tnut-y="{tnut_y}"/>'
                )
                svg_content.append(polygon)
                
            except Exception as e:
                print(f"Error adding blob to SVG: {e}")
                continue
        
        # Close SVG tags
        svg_content.extend(['</g>', '</svg>'])
        
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Write the SVG file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(svg_content))
            
    except Exception as e:
        raise Exception(f"Error saving SVG file: {str(e)}") 