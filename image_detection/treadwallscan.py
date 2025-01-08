import os
import cv2
from wall_scanner import process_image
from SVG_to_image_grid import convert_svg_to_jpeg_grid

def scan_treadwall(image_path, confidence_threshold=0.25, nms_iou_threshold=0.4):
    """
    Process a treadwall image to produce grid-aligned outputs:
    - Grid-aligned JPEG (converted_grid_*.jpg)
    - Grid-aligned SVG (*_grid.svg)
    """
    print(f"\nProcessing: {os.path.basename(image_path)}")
    
    try:
        # Step 1: Initial hold detection and SVG creation
        blobs, _ = process_image(
            image_path,
            confidence_threshold=confidence_threshold,
            nms_iou_threshold=nms_iou_threshold
        )
        
        # Get paths for grid processing
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        project_root = os.path.dirname(os.path.dirname(__file__))
        
        # Temporary SVG path for intermediate processing
        temp_svg = os.path.join(project_root, 'output', 'svg', f"{base_name}.svg")
        
        # Final output paths
        output_jpg = os.path.join(project_root, 'output', 'grid', f"converted_grid_{base_name}.jpg")
        output_svg = os.path.join(project_root, 'output', 'svg', 'grid', f"{base_name}_grid.svg")
        
        # Step 2: Grid alignment and final outputs
        convert_svg_to_jpeg_grid(temp_svg, output_jpg, output_svg, debug=False)
        
        # Clean up temporary files
        if os.path.exists(temp_svg):
            os.remove(temp_svg)
        
        print("\nOutputs saved:")
        print(f"- Grid JPEG: output/grid/converted_grid_{base_name}.jpg")
        print(f"- Grid SVG: output/svg/grid/{base_name}_grid.svg")
        
    except Exception as e:
        print(f"\nError during processing: {e}")
        raise

def main():
    """Main function to run the treadwall scanning pipeline."""
    # Get the absolute paths for the directories
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_dir = os.path.join(current_dir, "images")
    
    # List available images
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp')
    images = [f for f in os.listdir(image_dir) if f.lower().endswith(image_extensions)]
    
    if not images:
        print(f"No images found in {image_dir}")
        print("Please add some images and try again.")
        return
    
    # Display available images
    print("\nAvailable images:")
    for i, image in enumerate(images, 1):
        print(f"{i}. {image}")
    
    # Get user selection
    while True:
        try:
            choice = int(input("\nSelect an image number: "))
            if 1 <= choice <= len(images):
                selected_image = images[choice - 1]
                break
            print("Invalid selection. Please try again.")
        except ValueError:
            print("Please enter a valid number.")
    
    # Process the selected image
    image_path = os.path.join(image_dir, selected_image)
    scan_treadwall(image_path)

if __name__ == "__main__":
    main() 