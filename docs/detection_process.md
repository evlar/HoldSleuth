# Hold Detection and Shape Extraction Process

## Overview

The project utilizes two main models to detect and analyze climbing holds:

### YOLO Model
- **Purpose**: Detects climbing holds by identifying bounding boxes around potential holds.
- **Implementation**:
  - The YOLO model is initialized in the `YOLOHoldDetector` class, using a pre-trained model from the ultralytics package.
  - The `detect_holds` method processes an image to output bounding boxes for each detected hold.

### SAM Model
- **Purpose**: Refines the bounding boxes from YOLO to extract precise contours of the holds.
- **Implementation**:
  - The SAM model is used in the `SAMBlobExtractor` class.
  - The `extract_blobs` method takes bounding boxes from YOLO and refines them to get exact contours.

## Integration and Data Flow

The `process_image` function orchestrates the flow between YOLO and SAM:
1. Uses YOLO to detect holds
2. Passes the results to the SAM model for contour extraction
3. Outputs detailed information about each hold:
   - Contour
   - Center
   - Area
   - Confidence level
4. Creates a visual representation of the wall

## Model Setup

### YOLO Model
- Uses YOLOv8n pre-trained model by default
- Can be customized with a trained climbing hold model
- Located in `image_detection/yolo_hold_detector.py`

### SAM Model
- Uses the SAM ViT-H model
- Model file: `sam_vit_h_4b8939.pth`
- Should be placed in `image_detection/model/`

## Troubleshooting

### YOLO Model Issues
1. **Verify Model Path**:
   - The pre-trained YOLOv8n model will be downloaded automatically
   - For custom models, ensure the path is correctly set in `YOLOHoldDetector`

2. **Check Dependencies**:
   - Ensure ultralytics package is installed: `conda install -c conda-forge ultralytics`
   - Verify PyTorch installation

3. **Test with Sample Images**:
   - Use known sample images to verify detection
   - Check confidence scores in output
   - Adjust confidence threshold (default: 0.25) if needed

4. **Common Issues**:
   - Low confidence detections: Adjust threshold in `YOLOHoldDetector.detect_holds()`
   - No detections: Check if image is loaded correctly
   - Model loading errors: Verify CUDA/CPU compatibility

### SAM Model Issues
1. **Model File**:
   - Ensure `sam_vit_h_4b8939.pth` is in `image_detection/model/`
   - Download from [SAM releases](https://github.com/facebookresearch/segment-anything/releases/) if missing

2. **Memory Issues**:
   - SAM requires significant memory
   - Falls back to CPU if CUDA is unavailable
   - Reduce image size if needed

## Output Files

The process generates several output files in `image_detection/holds_detected/`:
1. `*_detected.jpg`: Visualization with bounding boxes and contours
2. `*.svg`: Vector graphics of hold outlines
3. Hold masks and other visualizations

## Performance Optimization

- Use GPU acceleration when available
- Adjust confidence thresholds based on your needs
- Consider image preprocessing for better results
- Balance between detection accuracy and processing speed 