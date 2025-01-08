import os
import cairosvg
from PIL import Image
import io
import xml.etree.ElementTree as ET
import cv2
import numpy as np
import matplotlib.pyplot as plt


def get_original_image_dimensions(svg_path):
    """Get dimensions from the original image file."""
    original_path = svg_path.replace('output/svg/', 'image_detection/images/').replace('.svg', '.jpg')
    try:
        with Image.open(original_path) as img:
            return img.size, original_path
    except Exception as e:
        print(f"Could not get original image dimensions: {e}")
        return None, None


def detect_tnuts(image_path, debug=False):
    """
    Detect t-nuts in the image using circle detection.
    Returns detected circles and optionally saves debug visualization.
    """
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not load image: {image_path}")
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply preprocessing to enhance t-nut visibility
    blurred = cv2.GaussianBlur(gray, (5, 5), 2)
    
    # Enhance contrast
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(blurred)
    
    # Try different parameter combinations for Hough Circles
    circle_params = [
        # (dp, minDist, param1, param2, minRadius, maxRadius)
        (1, 20, 50, 20, 2, 8),    # For smaller t-nuts
        (1, 30, 50, 25, 3, 10),   # Original parameters
        (1, 40, 50, 30, 4, 12),   # For larger t-nuts
    ]
    
    circles = None
    for dp, minDist, param1, param2, minRadius, maxRadius in circle_params:
        circles = cv2.HoughCircles(
            enhanced,
            cv2.HOUGH_GRADIENT,
            dp=dp,
            minDist=minDist,
            param1=param1,
            param2=param2,
            minRadius=minRadius,
            maxRadius=maxRadius
        )
        if circles is not None and len(circles[0]) > 10:  # If we find enough circles, stop
            break
    
    if debug:
        # Create debug visualization
        debug_img = img.copy()
        if circles is not None:
            circles = np.round(circles[0, :]).astype(int)
            for (x, y, r) in circles:
                # Draw the circle
                cv2.circle(debug_img, (x, y), r, (0, 255, 0), 2)
                # Draw the center
                cv2.circle(debug_img, (x, y), 2, (0, 0, 255), 3)
        
        # Save both the enhanced image and the detection result
        debug_path = image_path.replace('.jpg', '_tnuts_detected.jpg')
        cv2.imwrite(debug_path, debug_img)
        cv2.imwrite(image_path.replace('.jpg', '_enhanced.jpg'), enhanced)
        print(f"Saved t-nut detection visualization to: {debug_path}")
        print(f"Saved enhanced image to: {image_path.replace('.jpg', '_enhanced.jpg')}")
        
        if circles is not None:
            print(f"Detected {len(circles)} t-nuts")
        else:
            print("No t-nuts detected")
    
    if circles is not None:
        return np.round(circles[0, :]).astype(int)
    return None


def calculate_grid_parameters(tnut_positions, debug=False):
    """
    Calculate ideal grid parameters from detected t-nut positions.
    Returns grid parameters and optionally saves debug visualization.
    """
    if tnut_positions is None or len(tnut_positions) < 4:
        return None
    
    # Calculate typical spacing between t-nuts
    x_coords = tnut_positions[:, 0]
    y_coords = tnut_positions[:, 1]
    
    # Find most common x and y distances
    x_diffs = np.diff(np.sort(x_coords))
    y_diffs = np.diff(np.sort(y_coords))
    
    # Filter out very small differences and calculate median spacing
    x_diffs = x_diffs[x_diffs > 5]
    y_diffs = y_diffs[y_diffs > 5]
    
    if len(x_diffs) == 0 or len(y_diffs) == 0:
        return None
    
    grid_spacing_x = np.median(x_diffs)
    grid_spacing_y = np.median(y_diffs)
    
    grid_params = {
        'spacing_x': grid_spacing_x,
        'spacing_y': grid_spacing_y,
        'origin_x': np.min(x_coords),
        'origin_y': np.min(y_coords),
        'max_x': np.max(x_coords),
        'max_y': np.max(y_coords)
    }
    
    if debug:
        # Create debug visualization of grid
        plt.figure(figsize=(12, 8))
        plt.scatter(x_coords, y_coords, c='red', label='Detected T-nuts')
        
        # Draw grid lines
        x_grid = np.arange(grid_params['origin_x'], grid_params['max_x'], grid_spacing_x)
        y_grid = np.arange(grid_params['origin_y'], grid_params['max_y'], grid_spacing_y)
        
        for x in x_grid:
            plt.axvline(x, color='blue', alpha=0.3)
        for y in y_grid:
            plt.axhline(y, color='blue', alpha=0.3)
        
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.title('Detected T-nuts and Calculated Grid')
        
        # Save debug visualization
        debug_path = 'grid_visualization.png'
        plt.savefig(debug_path)
        plt.close()
        print(f"Saved grid visualization to: {debug_path}")
    
    return grid_params


def get_svg_viewbox(svg_root):
    """Extract viewBox parameters from SVG."""
    if 'viewBox' in svg_root.attrib:
        min_x, min_y, width, height = map(float, svg_root.attrib['viewBox'].split())
        return min_x, min_y, width, height
    return 0, 0, float(svg_root.get('width', 0)), float(svg_root.get('height', 0))


def transform_svg_to_grid(svg_root, grid_params, tnuts):
    """Move holds to align with t-nut grid positions while preserving their shapes."""
    if grid_params is None:
        return
    
    # Get SVG viewBox for coordinate transformation
    view_min_x, view_min_y, view_width, view_height = get_svg_viewbox(svg_root)
    
    # Calculate scaling factors if viewBox and actual dimensions differ
    width = float(svg_root.get('width', view_width))
    height = float(svg_root.get('height', view_height))
    scale_x = width / view_width if view_width else 1
    scale_y = height / view_height if view_height else 1
    
    # Keep track of occupied grid positions to handle duplicates
    occupied_positions = {}  # (grid_x, grid_y) -> (tnut_x, tnut_y)
    
    # First pass: collect all holds and their grid positions
    holds = []
    for polygon in svg_root.findall('.//{*}polygon'):
        points = polygon.get('points').split()
        
        # Parse all points and transform from viewBox to actual coordinates
        original_points = []
        for point in points:
            x, y = map(float, point.split(','))
            # Transform from viewBox to actual coordinates
            x = (x - view_min_x) * scale_x
            y = (y - view_min_y) * scale_y
            original_points.append((x, y))
        
        # Get t-nut location from metadata
        if 'data-tnut-x' in polygon.attrib and 'data-tnut-y' in polygon.attrib:
            tnut_x = float(polygon.get('data-tnut-x'))
            tnut_y = float(polygon.get('data-tnut-y'))
            # Transform from viewBox to actual coordinates
            tnut_x = (tnut_x - view_min_x) * scale_x
            tnut_y = (tnut_y - view_min_y) * scale_y
        else:
            # Calculate centroid
            tnut_x = sum(x for x, y in original_points) / len(original_points)
            tnut_y = sum(y for x, y in original_points) / len(original_points)
        
        # Find nearest t-nut
        distances = np.sqrt((tnuts[:, 0] - tnut_x)**2 + (tnuts[:, 1] - tnut_y)**2)
        nearest_tnut_idx = np.argmin(distances)
        nearest_tnut = tnuts[nearest_tnut_idx]
        
        # Calculate grid position
        grid_x = int((nearest_tnut[0] - grid_params['origin_x']) / grid_params['spacing_x'])
        grid_y = int((nearest_tnut[1] - grid_params['origin_y']) / grid_params['spacing_y'])
        grid_x = max(0, min(7, grid_x))
        grid_y = max(0, min(39, grid_y))
        
        holds.append({
            'polygon': polygon,
            'original_points': original_points,
            'tnut_x': tnut_x,
            'tnut_y': tnut_y,
            'grid_x': grid_x,
            'grid_y': grid_y,
            'nearest_tnut': nearest_tnut
        })
    
    # Sort holds by distance to their nearest t-nut
    for hold in holds:
        hold['distance'] = np.sqrt((hold['nearest_tnut'][0] - hold['tnut_x'])**2 + 
                                 (hold['nearest_tnut'][1] - hold['tnut_y'])**2)
    holds.sort(key=lambda h: h['distance'])
    
    # Second pass: transform holds, skipping duplicates
    for hold in holds:
        grid_pos = (hold['grid_x'], hold['grid_y'])
        
        # Skip if this grid position is already occupied by a closer hold
        if grid_pos in occupied_positions:
            continue
        
        occupied_positions[grid_pos] = (hold['nearest_tnut'][0], hold['nearest_tnut'][1])
        
        # Calculate the offset needed to move to nearest t-nut
        offset_x = hold['nearest_tnut'][0] - hold['tnut_x']
        offset_y = hold['nearest_tnut'][1] - hold['tnut_y']
        
        # Move all points by the offset (preserving shape)
        transformed_points = []
        for x, y in hold['original_points']:
            new_x = x + offset_x
            new_y = y + offset_y
            # Transform back to viewBox coordinates
            new_x = new_x / scale_x + view_min_x
            new_y = new_y / scale_y + view_min_y
            transformed_points.append(f"{new_x},{new_y}")
        
        # Update the polygon with new position
        hold['polygon'].set('points', ' '.join(transformed_points))
        
        # Add grid position metadata
        hold['polygon'].set('data-grid-x', str(hold['grid_x']))
        hold['polygon'].set('data-grid-y', str(hold['grid_y']))
        hold['polygon'].set('data-grid-position', f"{hold['grid_x']},{hold['grid_y']}")
        hold['polygon'].set('data-tnut-x', str(hold['nearest_tnut'][0]))
        hold['polygon'].set('data-tnut-y', str(hold['nearest_tnut'][1]))
        hold['polygon'].set('data-original-tnut-x', str(hold['tnut_x']))
        hold['polygon'].set('data-original-tnut-y', str(hold['tnut_y']))
        
        # Add color as metadata if it exists
        if 'fill' in hold['polygon'].attrib:
            hold['polygon'].set('data-color', hold['polygon'].get('fill'))


def get_hold_positions_from_svg(svg_root):
    """Extract hold positions from SVG."""
    hold_positions = []
    
    for polygon in svg_root.findall('.//{*}polygon'):
        points = polygon.get('points').split()
        x_coords = []
        y_coords = []
        
        # Calculate centroid of the hold
        for point in points:
            x, y = map(float, point.split(','))
            x_coords.append(x)
            y_coords.append(y)
        
        centroid_x = sum(x_coords) / len(x_coords)
        centroid_y = sum(y_coords) / len(y_coords)
        
        hold_positions.append((centroid_x, centroid_y))
    
    return np.array(hold_positions)


def infer_grid_from_holds(hold_positions, debug=False, base_name="unknown"):
    """
    Infer grid parameters from hold positions, using known 40x8 grid pattern.
    Uses clustering of distances to find common spacings.
    """
    if len(hold_positions) < 4:
        return None
    
    # Get image bounds
    min_x = np.min(hold_positions[:, 0])
    max_x = np.max(hold_positions[:, 0])
    min_y = np.min(hold_positions[:, 1])
    max_y = np.max(hold_positions[:, 1])
    
    # Calculate grid spacing based on known 40x8 grid
    # Add small padding to account for holds not exactly at edges
    width = max_x - min_x + 20  # Add padding
    height = max_y - min_y + 20  # Add padding
    
    # Grid spacing based on known dimensions
    grid_spacing_x = width / 8    # 8 columns
    grid_spacing_y = height / 40  # 40 rows
    
    # Adjust origin to account for padding
    origin_x = min_x - 10  # Half of padding
    origin_y = min_y - 10  # Half of padding
    
    grid_params = {
        'spacing_x': grid_spacing_x,
        'spacing_y': grid_spacing_y,
        'origin_x': origin_x,
        'origin_y': origin_y,
        'max_x': max_x + 10,
        'max_y': max_y + 10
    }
    
    if debug:
        # Create debug visualization
        plt.figure(figsize=(12, 24))  # Adjusted for typical wall aspect ratio
        
        # Plot hold positions
        plt.scatter(hold_positions[:, 0], hold_positions[:, 1], 
                   c='red', label='Hold Positions', s=50)
        
        # Draw inferred grid
        x_grid = np.linspace(grid_params['origin_x'], 
                            grid_params['max_x'], 
                            9)  # 8 columns + 1 for right edge
        y_grid = np.linspace(grid_params['origin_y'], 
                            grid_params['max_y'], 
                            41)  # 40 rows + 1 for bottom edge
        
        for x in x_grid:
            plt.axvline(x, color='blue', alpha=0.3)
        for y in y_grid:
            plt.axhline(y, color='blue', alpha=0.3)
        
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.title('Hold Positions and Standard 40x8 Grid')
        
        # Save visualization
        debug_dir = os.path.join(os.getcwd(), 'output', 'debug_visualizations')
        os.makedirs(debug_dir, exist_ok=True)
        debug_path = os.path.join(debug_dir, f"{base_name}_grid_inference.png")
        plt.savefig(debug_path, bbox_inches='tight', dpi=300)
        plt.close()
        print(f"Saved grid inference visualization to: {debug_path}")
        
        # Also plot histograms of distances
        plt.figure(figsize=(12, 4))
        plt.subplot(121)
        plt.hist(np.diff(x_grid), bins=20)
        plt.title('X Grid Spacing')
        plt.axvline(grid_spacing_x, color='r', linestyle='--')
        
        plt.subplot(122)
        plt.hist(np.diff(y_grid), bins=20)
        plt.title('Y Grid Spacing')
        plt.axvline(grid_spacing_y, color='r', linestyle='--')
        
        plt.tight_layout()
        dist_path = os.path.join(debug_dir, f"{base_name}_grid_inference_distributions.png")
        plt.savefig(dist_path)
        plt.close()
        print(f"Saved grid inference distributions to: {dist_path}")
    
    return grid_params


def get_hold_range(svg_root):
    """Get the actual range of hold positions from the SVG."""
    min_x = float('inf')
    max_x = float('-inf')
    min_y = float('inf')
    max_y = float('-inf')
    
    for polygon in svg_root.findall('.//{*}polygon'):
        if 'data-tnut-x' in polygon.attrib and 'data-tnut-y' in polygon.attrib:
            x = float(polygon.get('data-tnut-x'))
            y = float(polygon.get('data-tnut-y'))
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)
    
    if min_x == float('inf'):
        return None
    return min_x, max_x, min_y, max_y


def generate_tnut_grid(width, height, svg_root=None):
    """Generate t-nut positions based on the known 8x40 grid pattern."""
    # Try to get actual hold range from SVG
    hold_range = None if svg_root is None else get_hold_range(svg_root)
    
    if hold_range:
        min_x, max_x, min_y, max_y = hold_range
        # Use actual hold range to determine grid spacing
        grid_width = max_x - min_x
        grid_height = max_y - min_y
        grid_spacing_x = grid_width / 7  # 7 intervals for 8 columns
        grid_spacing_y = grid_height / 39  # 39 intervals for 40 rows
        
        # Use actual min positions as origin
        origin_x = min_x
        origin_y = min_y
    else:
        # Fallback to using image dimensions
        grid_spacing_x = width / 8     # 8 columns
        grid_spacing_y = height / 40   # 40 rows
        origin_x = grid_spacing_x / 2  # Half a spacing from the left edge
        origin_y = grid_spacing_y / 2  # Half a spacing from the top edge
    
    # Calculate grid dimensions
    grid_width = grid_spacing_x * 8
    grid_height = grid_spacing_y * 40
    
    # Generate all t-nut positions
    tnuts = []
    for y in range(40):  # 40 rows
        for x in range(8):  # 8 columns
            tnut_x = origin_x + x * grid_spacing_x
            tnut_y = origin_y + y * grid_spacing_y
            tnuts.append([tnut_x, tnut_y])
    
    grid_params = {
        'spacing_x': grid_spacing_x,
        'spacing_y': grid_spacing_y,
        'origin_x': origin_x,
        'origin_y': origin_y,
        'max_x': origin_x + grid_width,
        'max_y': origin_y + grid_height
    }
    
    return np.array(tnuts), grid_params


def parse_svg_file(svg_path):
    """Parse SVG file with robust error handling."""
    try:
        # First try direct parsing
        parser = ET.XMLParser(encoding="utf-8")
        tree = ET.parse(svg_path, parser=parser)
        return tree
    except ET.ParseError as e:
        print(f"XML parsing error: {e}")
        # Try to fix common XML issues
        with open(svg_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # Remove any empty lines at the start
        content = '\n'.join(line for line in content.splitlines() if line.strip())
        
        # Ensure proper XML structure
        if not content.startswith('<?xml'):
            content = '<?xml version="1.0" encoding="utf-8"?>\n' + content
        
        if not '<svg' in content:
            content = content.replace('<?xml version="1.0" encoding="utf-8"?>\n',
                                   '<?xml version="1.0" encoding="utf-8"?>\n<svg xmlns="http://www.w3.org/2000/svg">\n')
            content += '\n</svg>'
        
        # Write fixed content to temporary file
        temp_svg = svg_path + '.temp'
        with open(temp_svg, 'w', encoding='utf-8') as f:
            f.write(content)
        
        try:
            # Try parsing the fixed file
            tree = ET.parse(temp_svg, parser=parser)
            os.remove(temp_svg)
            return tree
        except ET.ParseError as e2:
            if os.path.exists(temp_svg):
                os.remove(temp_svg)
            print(f"Could not parse SVG file even after fixes: {e2}")
            print("SVG content:")
            print(content[:500] + "..." if len(content) > 500 else content)
            raise


def convert_svg_to_jpeg_grid(svg_path, output_jpg_path, output_svg_path, debug=False):
    """Convert SVG to JPEG, snapping holds to t-nut grid positions."""
    try:
        # Get original image dimensions and path
        (width, height), original_image_path = get_original_image_dimensions(svg_path)
        if width is None or original_image_path is None:
            raise ValueError("Could not get original image information")
        
        print(f"Processing SVG: {svg_path}")
        print(f"Will save grid SVG to: {output_svg_path}")
        
        # Parse SVG file first to get hold positions
        tree = parse_svg_file(svg_path)
        root = tree.getroot()
        
        # Generate t-nut positions based on grid
        print("Generating t-nut grid...")
        tnuts, grid_params = generate_tnut_grid(width, height, root)
        print(f"Generated {len(tnuts)} t-nut positions")
        
        # Set explicit dimensions and preserve viewBox
        root.set('width', str(width))
        root.set('height', str(height))
        if 'viewBox' not in root.attrib:
            root.set('viewBox', f"0 0 {width} {height}")
        
        # Get hold positions
        hold_positions = get_hold_positions_from_svg(root)
        print(f"Found {len(hold_positions)} holds")
        
        # Transform holds to align with grid
        transform_svg_to_grid(root, grid_params, tnuts)
        print("Aligned holds to grid positions")
        
        # Add grid parameters to SVG root
        root.set('data-grid-spacing-x', str(grid_params['spacing_x']))
        root.set('data-grid-spacing-y', str(grid_params['spacing_y']))
        root.set('data-grid-origin-x', str(grid_params['origin_x']))
        root.set('data-grid-origin-y', str(grid_params['origin_y']))
        root.set('data-grid-columns', '8')
        root.set('data-grid-rows', '40')
        
        if debug:
            # Create debug visualization
            plt.figure(figsize=(12, 24))
            
            # Plot t-nut positions
            plt.scatter(tnuts[:, 0], tnuts[:, 1], 
                       c='green', alpha=0.5, label='T-nut Positions', s=20)
            
            # Plot original hold positions
            plt.scatter(hold_positions[:, 0], hold_positions[:, 1], 
                       c='red', alpha=0.5, label='Original Hold Positions', s=50)
            
            # Plot grid-aligned positions
            aligned_positions = []
            for polygon in root.findall('.//{*}polygon'):
                x = float(polygon.get('data-tnut-x'))
                y = float(polygon.get('data-tnut-y'))
                aligned_positions.append((x, y))
            
            if aligned_positions:
                aligned_positions = np.array(aligned_positions)
                plt.scatter(aligned_positions[:, 0], aligned_positions[:, 1],
                           c='blue', alpha=0.5, label='Grid-Aligned Holds', s=50)
            
            # Draw grid lines
            x_grid = np.arange(grid_params['origin_x'], grid_params['max_x'] + grid_params['spacing_x'], grid_params['spacing_x'])
            y_grid = np.arange(grid_params['origin_y'], grid_params['max_y'] + grid_params['spacing_y'], grid_params['spacing_y'])
            
            for x in x_grid:
                plt.axvline(x, color='gray', alpha=0.3)
            for y in y_grid:
                plt.axhline(y, color='gray', alpha=0.3)
            
            plt.grid(True, alpha=0.3)
            plt.legend()
            plt.title('T-nuts (Green), Original Holds (Red), and Grid-Aligned Holds (Blue)')
            plt.gca().set_aspect('equal', adjustable='box')
            
            # Set plot limits to image dimensions with padding
            plt.xlim(-10, width + 10)
            plt.ylim(-10, height + 10)
            
            # Save visualization
            base_name = os.path.splitext(os.path.basename(svg_path))[0]
            debug_dir = os.path.join(os.path.dirname(os.path.dirname(svg_path)), 'debug_visualizations')
            os.makedirs(debug_dir, exist_ok=True)
            debug_path = os.path.join(debug_dir, f"{base_name}_grid_visualization.png")
            plt.savefig(debug_path, bbox_inches='tight', dpi=300)
            plt.close()
            print(f"Saved grid visualization to: {debug_path}")
            
            # Also save distance distributions
            plt.figure(figsize=(12, 4))
            plt.subplot(121)
            plt.hist(np.diff(x_grid), bins=20)
            plt.title('X Grid Spacing')
            plt.axvline(grid_params['spacing_x'], color='r', linestyle='--')
            
            plt.subplot(122)
            plt.hist(np.diff(y_grid), bins=20)
            plt.title('Y Grid Spacing')
            plt.axvline(grid_params['spacing_y'], color='r', linestyle='--')
            
            plt.tight_layout()
            dist_path = os.path.join(debug_dir, f"{base_name}_distance_distributions.png")
            plt.savefig(dist_path)
            plt.close()
            print(f"Saved distance distributions to: {dist_path}")

        # Save the grid-aligned SVG
        try:
            os.makedirs(os.path.dirname(output_svg_path), exist_ok=True)
            tree.write(output_svg_path, encoding='utf-8', xml_declaration=True)
            print(f"Successfully saved grid-aligned SVG to: {output_svg_path}")
            
            # Convert SVG to JPEG
            # Save modified SVG to temporary file
            temp_svg = svg_path + '.temp'
            tree.write(temp_svg)
            
            try:
                # Convert SVG to PNG first with dimensions
                png_data = cairosvg.svg2png(url=temp_svg, output_width=int(width), output_height=int(height))
                
                # Convert PNG data to JPEG using Pillow
                image = Image.open(io.BytesIO(png_data))
                image = image.convert('RGB')  # Ensure it's in RGB mode
                image.save(output_jpg_path, 'JPEG', quality=95)
                print(f"Saved grid-aligned JPEG to: {output_jpg_path}")
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_svg):
                    os.remove(temp_svg)
            
        except Exception as e:
            print(f"Error saving files: {e}")
                
    except Exception as e:
        print(f"Failed to process SVG: {e}")
        raise


def main():
    # Directory containing SVG files
    svg_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output/svg')

    # Ensure the output directories exist
    output_jpg_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output/grid')
    output_svg_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output/svg/grid')
    os.makedirs(output_jpg_dir, exist_ok=True)
    os.makedirs(output_svg_dir, exist_ok=True)

    # Convert each SVG file in the directory
    for file_name in os.listdir(svg_dir):
        if file_name.endswith('.svg') and not file_name.endswith('_grid.svg'):
            svg_path = os.path.join(svg_dir, file_name)
            base_name = file_name.replace('.svg', '')
            output_jpg_path = os.path.join(output_jpg_dir, f"converted_grid_{base_name}.jpg")
            output_svg_path = os.path.join(output_svg_dir, f"{base_name}_grid.svg")
            
            try:
                convert_svg_to_jpeg_grid(svg_path, output_jpg_path, output_svg_path, debug=True)
            except Exception as e:
                print(f"Error processing {file_name}: {e}")


if __name__ == '__main__':
    main() 