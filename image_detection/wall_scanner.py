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
    import svgwrite
    
    # Create SVG drawing with the same dimensions as the image
    dwg = svgwrite.Drawing(output_path, profile='tiny')
    
    # Add holds to the SVG
    for blob in blobs:
        # Convert contour points to SVG polygon points
        points = [(int(x), int(y)) for x, y in blob.contour.reshape(-1, 2)]
        # Add polygon with hold color
        dwg.add(dwg.polygon(points, 
                           fill=blob.color if blob.color != "unknown" else "#808080",
                           stroke="#000000",
                           stroke_width=1,
                           opacity=0.5))
    
    # Save the SVG file
    dwg.save()
    print(f"Saved SVG to: {output_path}")

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