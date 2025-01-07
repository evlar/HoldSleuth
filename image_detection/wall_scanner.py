import os
import cv2
import numpy as np
from image_detection.yolo_hold_detector import YOLOHoldDetector
from image_detection.sam_blob_extractor import SAMBlobExtractor

def list_images(image_dir):
    """List all images in the specified directory."""
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp')
    images = []
    
    for file in os.listdir(image_dir):
        if file.lower().endswith(image_extensions):
            images.append(file)
    
    return images

def select_image(images):
    """Let user select an image from the list."""
    if not images:
        raise ValueError("No images found in the images directory")
    
    print("\nAvailable images:")
    for i, image in enumerate(images, 1):
        print(f"{i}. {image}")
    
    while True:
        try:
            choice = int(input("\nSelect an image number: "))
            if 1 <= choice <= len(images):
                return images[choice - 1]
            print("Invalid selection. Please try again.")
        except ValueError:
            print("Please enter a valid number.")

def process_image(image_path):
    """Process an image to detect holds using YOLO and SAM."""
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Failed to load image: {image_path}")
    
    # Initialize detectors with default model paths
    yolo_detector = YOLOHoldDetector()  # Will use default model path from the class
    blob_extractor = SAMBlobExtractor()  # Will use default SAM model path
    
    # Detect holds using YOLO
    print("Detecting holds with YOLO...")
    holds = yolo_detector.detect_holds(image)
    print(f"Found {len(holds)} holds")
    
    # Extract precise shapes using SAM
    print("Extracting precise shapes with SAM...")
    blobs = blob_extractor.extract_blobs(image, holds)
    print(f"Processed {len(blobs)} holds")
    
    # Print results
    for blob in blobs:
        print(f"Hold center: {blob.center}, Color: {blob.color}, Confidence: {blob.confidence}")
    
    # Create visualization
    result_image = blob_extractor.draw_blobs(image, blobs)
    
    # Save visualization
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    output_image_path = os.path.join(os.path.dirname(image_path), f"{base_name}_detected.jpg")
    cv2.imwrite(output_image_path, result_image)
    print(f"Saved visualization to: {output_image_path}")
    
    return blobs

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
                
                # Create polygon with hold color and t-nut location metadata
                color = blob.color if blob.color != "unknown" else "#808080"
                tnut_x = float(blob.center[0])
                tnut_y = float(blob.center[1])
                
                polygon = (
                    f'<polygon points="{points_str}" '
                    f'fill="{color}" '
                    f'stroke="#000000" '
                    f'stroke-width="1" '
                    f'opacity="0.5" '
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
        
        # Verify the file was created and has content
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"Successfully saved SVG to: {output_path}")
        else:
            print(f"Warning: SVG file may be empty or not created properly at: {output_path}")
            
    except Exception as e:
        print(f"Error saving SVG file: {e}")
        raise

def main():
    # Get the absolute paths for the directories
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_dir = os.path.join(current_dir, "images")
    holds_detected_dir = os.path.join(current_dir, "holds_detected")
    
    # Ensure the holds_detected directory exists
    os.makedirs(holds_detected_dir, exist_ok=True)
    
    # List and select image
    images = list_images(image_dir)
    if not images:
        print(f"No images found in {image_dir}")
        print("Please add some images and try again.")
        return
    
    selected_image = select_image(images)
    image_path = os.path.join(image_dir, selected_image)
    print(f"\nProcessing image: {selected_image}")
    
    try:
        # Process the image and get the detected holds
        blobs = process_image(image_path)
        
        # Save the results as SVG
        base_name = os.path.splitext(selected_image)[0]
        svg_path = os.path.join(holds_detected_dir, f"{base_name}.svg")
        save_as_svg(blobs, svg_path)
        
    except Exception as e:
        print(f"Error processing image: {e}")

if __name__ == "__main__":
    main()