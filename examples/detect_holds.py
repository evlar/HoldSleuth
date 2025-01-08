import cv2
import os
from image_detection.wall_scanner import process_image

def main():
    """Example script demonstrating the complete hold detection pipeline."""
    # Get paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    image_dir = os.path.join(project_root, 'image_detection', 'images')
    
    # Ensure output directories exist
    output_dirs = [
        os.path.join(project_root, 'output', dir_name)
        for dir_name in ['raw_detections', 'svg', 'jpeg', 'grid', 'debug_visualizations']
    ]
    for dir_path in output_dirs:
        os.makedirs(dir_path, exist_ok=True)

    # Example image path - you'll need to add your own image
    image_path = os.path.join(image_dir, 'example.jpg')  # Using the default example image
    if not os.path.exists(image_path):
        print(f"Please add an image at {image_path}")
        print("You can use any climbing wall image, preferably with visible holds")
        return

    print("Starting hold detection pipeline...")
    print(f"Processing image: {image_path}")
    
    try:
        # Process the image - this will:
        # 1. Detect holds using YOLO
        # 2. Extract precise shapes using SAM
        # 3. Save detection visualization to output/raw_detections/
        # 4. Save SVG to output/svg/
        blobs, detection_img = process_image(
            image_path,
            confidence_threshold=0.25,  # Standard confidence threshold
            nms_iou_threshold=0.4       # Standard NMS threshold
        )
        
        print("\nProcessing complete!")
        print(f"Found {len(blobs)} holds")
        print("\nOutput files have been saved to:")
        print("- Raw detections: output/raw_detections/")
        print("- SVG files: output/svg/")
        print("- JPEG conversions: output/jpeg/")
        print("- Grid-aligned files: output/grid/")
        print("- Debug visualizations: output/debug_visualizations/")
        
    except Exception as e:
        print(f"Error processing image: {e}")

if __name__ == '__main__':
    main() 