import os
from image_detection.treadwallscan import scan_treadwall

def process_wall_scan(image_path):
    """
    Process a wall scan image and return the paths to the generated files.
    
    Args:
        image_path (str): Path to the uploaded image file
        
    Returns:
        tuple: (svg_path, grid_jpg_path) relative paths to the generated files
    """
    try:
        # Process the image using the existing treadwall scanner
        scan_treadwall(image_path)
        
        # Get the base filename without extension
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        
        # Construct relative paths to the generated files
        svg_path = os.path.join('output', 'svg', 'grid', f"{base_name}_grid.svg")
        grid_jpg_path = os.path.join('output', 'grid', f"converted_grid_{base_name}.jpg")
        
        # Verify files were created
        if not os.path.exists(svg_path) or not os.path.exists(grid_jpg_path):
            raise FileNotFoundError("Scanner failed to generate output files")
            
        return svg_path, grid_jpg_path
        
    except Exception as e:
        raise Exception(f"Error processing wall scan: {str(e)}") 