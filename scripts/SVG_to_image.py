import os
import cairosvg
from PIL import Image
import io
import xml.etree.ElementTree as ET


def get_original_image_dimensions(svg_path):
    """Get dimensions from the original image file."""
    # Get the original image path by converting the SVG path
    original_path = svg_path.replace('/holds_detected/', '/images/').replace('.svg', '.jpg')
    try:
        with Image.open(original_path) as img:
            return img.size
    except Exception as e:
        print(f"Could not get original image dimensions: {e}")
        return None


def get_svg_info(svg_path):
    """Extract dimensions and viewBox from SVG file."""
    try:
        # First try to get dimensions from original image
        original_dims = get_original_image_dimensions(svg_path)
        
        # Parse SVG
        tree = ET.parse(svg_path)
        root = tree.getroot()
        
        # Get viewport dimensions
        width = root.get('width')
        height = root.get('height')
        viewbox = root.get('viewBox')
        
        if original_dims:
            width, height = original_dims
        elif width == '100%' or height == '100%':
            if viewbox:
                min_x, min_y, vb_width, vb_height = map(float, viewbox.split())
                width, height = vb_width, vb_height
            else:
                width, height = 1920, 1080  # Default HD resolution
        else:
            width, height = float(width), float(height)
            
        return width, height, viewbox
        
    except Exception as e:
        print(f"Using default dimensions due to: {e}")
        return 1920, 1080, None


def convert_svg_to_jpeg(svg_path, output_path):
    """Convert an SVG file to a JPEG file preserving original dimensions and position."""
    try:
        # Get dimensions and viewBox
        width, height, viewbox = get_svg_info(svg_path)
        
        # Create a new SVG with proper positioning
        tree = ET.parse(svg_path)
        root = tree.getroot()
        
        # Set explicit dimensions
        root.set('width', str(width))
        root.set('height', str(height))
        
        # If viewBox exists, remove it to ensure proper scaling
        if 'viewBox' in root.attrib:
            del root.attrib['viewBox']
        
        # Save modified SVG to temporary file
        temp_svg = svg_path + '.temp'
        tree.write(temp_svg)
        
        try:
            # Convert SVG to PNG first with dimensions
            png_data = cairosvg.svg2png(url=temp_svg, output_width=int(width), output_height=int(height))

            # Convert PNG data to JPEG using Pillow
            image = Image.open(io.BytesIO(png_data))
            image = image.convert('RGB')  # Ensure it's in RGB mode
            image.save(output_path, 'JPEG', quality=95)  # Use high quality for better hold representation

            print(f"Converted {svg_path} to {output_path} with dimensions {width}x{height}")
        finally:
            # Clean up temporary file
            if os.path.exists(temp_svg):
                os.remove(temp_svg)
                
    except Exception as e:
        print(f"Failed to convert {svg_path} to JPEG: {e}")


def main():
    # Directory containing SVG files
    svg_dir = os.path.join(os.path.dirname(__file__), '../image_detection/holds_detected')

    # Ensure the output directory exists
    output_dir = os.path.join(svg_dir, 'converted_jpegs')
    os.makedirs(output_dir, exist_ok=True)

    # Convert each SVG file in the directory
    for file_name in os.listdir(svg_dir):
        if file_name.endswith('.svg'):
            svg_path = os.path.join(svg_dir, file_name)
            base_name = file_name.replace('.svg', '')
            output_path = os.path.join(output_dir, f"converted_{base_name}.jpg")
            convert_svg_to_jpeg(svg_path, output_path)


if __name__ == '__main__':
    main() 