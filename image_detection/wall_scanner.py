import os
import cv2
import numpy as np
from image_detection.yolo_hold_detector import YOLOHoldDetector, Hold
from image_detection.sam_blob_extractor import SAMBlobExtractor
import matplotlib.pyplot as plt

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

def process_image(image_path, confidence_threshold=0.05, nms_iou_threshold=0.4, model_path=None, device=None):
    """Process an image and return detected holds."""
    # Load image
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
    
    # Initialize detectors with default model paths
    yolo_detector = YOLOHoldDetector(
        confidence_threshold=confidence_threshold,
        nms_iou_threshold=nms_iou_threshold
    )
    blob_extractor = SAMBlobExtractor()
    
    # Detect holds using YOLO
    print("Detecting holds with YOLO...")
    holds = yolo_detector.detect_holds(image)
    print(f"Found {len(holds)} holds")
    
    # Allow manual selection of undetected holds
    holds = manual_selection(image, holds, yolo_detector)
    
    # Extract precise shapes using SAM
    print("Extracting precise shapes with SAM...")
    blobs = blob_extractor.extract_blobs(image, holds)
    print(f"Processed {len(blobs)} holds")
    
    # Print results
    for blob in blobs:
        print(f"Hold center: {blob.center}, Color: {blob.color}, Confidence: {blob.confidence}")
    
    # Create visualization
    result_image = blob_extractor.draw_blobs(image, blobs)
    
    # Save detection visualization
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
    
    # Create output directories if they don't exist
    raw_dir = os.path.join(output_dir, 'raw_detections')
    svg_dir = os.path.join(output_dir, 'svg')
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(svg_dir, exist_ok=True)
    
    # Save detection visualization
    detection_path = os.path.join(raw_dir, f"{base_name}_detected.jpg")
    cv2.imwrite(detection_path, result_image)
    
    # Save SVG
    svg_path = os.path.join(svg_dir, f"{base_name}.svg")
    save_as_svg(blobs, svg_path)
    
    return blobs, result_image

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

def manual_selection(image, detected_holds, yolo_detector):
    """Allow user to manually select undetected holds by clicking on the image."""
    # Draw detected holds on the image
    result_image = yolo_detector.draw_holds(image, detected_holds)

    # Display the image with detected holds
    fig, ax = plt.subplots()
    ax.imshow(cv2.cvtColor(result_image, cv2.COLOR_BGR2RGB))
    plt.title('Left click: place t-nut, Left click+drag: draw box\nRight-click: remove detection, Z: undo, Enter: done\nHold Shift: mouse wheel to zoom, click+drag to pan')

    # Enable zooming and panning
    ax.set_position([0.05, 0.05, 0.9, 0.9])
    plt.gcf().set_size_inches(12, 8)
    
    # Store state
    selected_holds = []
    current_center = None
    rect = None
    preview_rect = None
    markers = []
    deselected_markers = []
    shift_pressed = False
    panning = False
    last_pan_pos = None
    
    # Store visual elements for detected holds
    detected_rects = []
    for hold in detected_holds:
        x1, y1, x2, y2 = hold.bbox
        rect = plt.Rectangle((x1, y1), x2-x1, y2-y1, fill=False, color='g')
        ax.add_patch(rect)
        detected_rects.append({'hold': hold, 'rect': rect})

    def mark_deselected(center_x, center_y, size=20):
        """Draw a red X at the specified location."""
        line1 = ax.plot([center_x - size/2, center_x + size/2],
                       [center_y - size/2, center_y + size/2],
                       'r-', linewidth=2)[0]
        line2 = ax.plot([center_x - size/2, center_x + size/2],
                       [center_y + size/2, center_y - size/2],
                       'r-', linewidth=2)[0]
        deselected_markers.extend([line1, line2])

    def onclick(event):
        nonlocal current_center, shift_pressed, panning, last_pan_pos
        if shift_pressed:
            if event.button == 1:  # Left click for panning
                panning = True
                last_pan_pos = (event.xdata, event.ydata)
            return
        if event.button == 1:  # Left click
            if event.xdata is not None and event.ydata is not None:
                current_center = (int(event.xdata), int(event.ydata))
                marker = ax.plot(current_center[0], current_center[1], 'ro')[0]
                markers.append(marker)
                fig.canvas.draw()
        elif event.button == 3:  # Right click
            # Check if click is inside any detected hold
            click_point = (event.xdata, event.ydata)
            for i, rect_data in enumerate(detected_rects):
                hold = rect_data['hold']
                x1, y1, x2, y2 = hold.bbox
                if (x1 <= click_point[0] <= x2 and y1 <= click_point[1] <= y2):
                    rect_data['rect'].remove()
                    detected_holds.remove(hold)
                    detected_rects.pop(i)
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    mark_deselected(center_x, center_y)
                    fig.canvas.draw()
                    break

    def onmotion(event):
        nonlocal preview_rect, shift_pressed, panning, last_pan_pos
        if shift_pressed and panning and last_pan_pos is not None:
            # Handle panning
            if event.xdata is not None and event.ydata is not None:
                dx = event.xdata - last_pan_pos[0]
                dy = event.ydata - last_pan_pos[1]
                
                # Get current limits
                x1, x2 = ax.get_xlim()
                y1, y2 = ax.get_ylim()
                
                # Update limits
                ax.set_xlim(x1 - dx, x2 - dx)
                ax.set_ylim(y1 - dy, y2 - dy)
                
                fig.canvas.draw()
            return
            
        if current_center and event.xdata is not None and event.ydata is not None:
            x2, y2 = int(event.xdata), int(event.ydata)
            x1 = min(current_center[0], x2)
            y1 = min(current_center[1], y2)
            x2 = max(current_center[0], x2)
            y2 = max(current_center[1], y2)
            
            if preview_rect:
                preview_rect.remove()
            preview_rect = plt.Rectangle((x1, y1), x2-x1, y2-y1, fill=False, color='r', linestyle='--')
            ax.add_patch(preview_rect)
            fig.canvas.draw()

    def onrelease(event):
        nonlocal current_center, rect, preview_rect, shift_pressed, panning, last_pan_pos
        if shift_pressed:
            panning = False
            last_pan_pos = None
            return
        if current_center and event.xdata is not None and event.ydata is not None:
            x2, y2 = int(event.xdata), int(event.ydata)
            x1 = min(current_center[0], x2)
            y1 = min(current_center[1], y2)
            x2 = max(current_center[0], x2)
            y2 = max(current_center[1], y2)
            
            if preview_rect:
                preview_rect.remove()
                preview_rect = None
            
            if rect:
                rect.remove()
            rect = plt.Rectangle((x1, y1), x2-x1, y2-y1, fill=False, color='r')
            ax.add_patch(rect)
            
            selected_holds.append({
                'hold': Hold(
                    center=current_center,
                    bbox=(x1, y1, x2, y2),
                    confidence=1.0,
                    color='gray'
                ),
                'rect': rect,
                'marker': markers[-1] if markers else None
            })
            
            current_center = None
            rect = None
            fig.canvas.draw()

    def onscroll(event):
        if shift_pressed and event.inaxes == ax:
            # Get the current x and y limits
            cur_xlim = ax.get_xlim()
            cur_ylim = ax.get_ylim()
            
            # Get the cursor position
            xdata = event.xdata
            ydata = event.ydata
            
            # Get the zoom factor
            base_scale = 1.1
            if event.button == 'up':
                scale_factor = 1 / base_scale
            else:
                scale_factor = base_scale
            
            # Calculate new limits
            new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
            new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
            
            # Set new limits centered on cursor position
            ax.set_xlim([xdata - new_width * (xdata - cur_xlim[0]) / (cur_xlim[1] - cur_xlim[0]),
                        xdata + new_width * (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])])
            ax.set_ylim([ydata - new_height * (ydata - cur_ylim[0]) / (cur_ylim[1] - cur_ylim[0]),
                        ydata + new_height * (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])])
            
            fig.canvas.draw()

    def on_key(event):
        nonlocal current_center, rect, preview_rect, shift_pressed, panning, last_pan_pos
        if event.key == 'enter':
            for marker in deselected_markers:
                marker.remove()
            plt.close(fig)
        elif event.key == 'z' and selected_holds:  # Undo last selection
            last_hold = selected_holds.pop()
            if last_hold['rect']:
                last_hold['rect'].remove()
            if last_hold['marker']:
                last_hold['marker'].remove()
            fig.canvas.draw()
        elif event.key == 'shift':  # Enable zoom/pan while shift is held
            shift_pressed = True
        elif event.key == 'shift+up':  # Disable zoom/pan when shift is released
            shift_pressed = False
            panning = False
            last_pan_pos = None

    # Connect event handlers
    toolbar = fig.canvas.toolbar
    fig.canvas.mpl_connect('button_press_event', onclick)
    fig.canvas.mpl_connect('motion_notify_event', onmotion)
    fig.canvas.mpl_connect('button_release_event', onrelease)
    fig.canvas.mpl_connect('key_press_event', on_key)
    fig.canvas.mpl_connect('key_release_event', lambda event: on_key(type('Event', (), {'key': 'shift+up'})))
    fig.canvas.mpl_connect('scroll_event', onscroll)
    plt.show()

    detected_holds.extend(hold_data['hold'] for hold_data in selected_holds)
    return detected_holds

def main():
    # Get the absolute paths for the directories
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_dir = os.path.join(current_dir, "images")
    output_dir = os.path.join(os.path.dirname(current_dir), "output")
    
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
        # Process the image with default thresholds
        blobs, detection_img = process_image(
            image_path,
            confidence_threshold=0.25,  # Standard confidence threshold
            nms_iou_threshold=0.4       # Standard NMS threshold
        )
        
    except Exception as e:
        print(f"Error processing image: {e}")

if __name__ == "__main__":
    main()