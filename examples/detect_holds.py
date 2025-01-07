import cv2
import os
from image_detection.yolo_hold_detector import YOLOHoldDetector
from image_detection.sam_blob_extractor import SAMBlobExtractor

def main():
    # Initialize detectors
    yolo_detector = YOLOHoldDetector()
    sam_extractor = SAMBlobExtractor()

    # Load an image
    image_path = os.path.join('data', 'sample_wall.jpg')  # You'll need to add your own image
    if not os.path.exists(image_path):
        print(f"Please add a sample image at {image_path}")
        return

    # Read and process image
    image = cv2.imread(image_path)
    if image is None:
        print("Failed to load image")
        return

    # Detect holds
    holds = yolo_detector.detect_holds(image)
    print(f"Detected {len(holds)} holds")

    # Draw hold detections
    hold_viz = yolo_detector.draw_holds(image, holds)
    cv2.imwrite(os.path.join('data', 'detected_holds.jpg'), hold_viz)

    # Extract precise shapes
    blobs = sam_extractor.extract_blobs(image, holds)
    print(f"Extracted {len(blobs)} precise hold shapes")

    # Draw blob visualization
    blob_viz = sam_extractor.draw_blobs(image, blobs)
    cv2.imwrite(os.path.join('data', 'extracted_blobs.jpg'), blob_viz)

    # Create mask visualization
    mask_viz = sam_extractor.create_mask_visualization(image, blobs)
    cv2.imwrite(os.path.join('data', 'hold_masks.jpg'), mask_viz)

if __name__ == '__main__':
    main() 