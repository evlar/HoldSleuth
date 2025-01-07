# HoldSleuth

A computer vision project for detecting and analyzing climbing holds using multiple detection methods.

## Overview

This project explores different approaches to climbing hold detection:
- Image-based detection using YOLO and SAM (Segment Anything Model)
- [Planned] Real-time video feed detection
- [Planned] Microsoft Kinect scanner integration

For detailed information about the detection process, see [Detection Process Documentation](docs/detection_process.md).

## Features

- YOLO-based hold detection with color classification
- Precise hold shape extraction using SAM
- Hold property analysis (area, contours, convex hull)
- [Planned] Real-time detection from video feed
- [Planned] 3D scanning capabilities

## Credits

This project uses the following models:

- **YOLO Model**: The climbing hold detection model (`best.pt`) is from [climbingcrux_model](https://github.com/mkurc1/climbingcrux_model) by [mkurc1](https://github.com/mkurc1)
- **SAM Model**: Uses the Segment Anything Model architecture from [Meta Research](https://github.com/facebookresearch/segment-anything). The `sam_vit_h_4b8939.pth` weights file can be downloaded from their [releases page](https://github.com/facebookresearch/segment-anything/releases/).

## Requirements

See `requirements.txt` for a complete list of dependencies.

## Required Model Files

This project requires two model files that need to be downloaded separately due to their size:

1. **SAM Model** (`sam_vit_h_4b8939.pth`):
   ```bash
   # Download SAM model to the models directory
   mkdir -p models
   cd models
   wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth
   cd ..
   ```
   - Or download manually from [SAM Releases](https://github.com/facebookresearch/segment-anything/releases/)
   - Place in the `models/` directory
   - Used for precise hold shape extraction

2. **YOLO Model** (`best.pt`):
   - Download from [climbingcrux_model](https://github.com/mkurc1/climbingcrux_model) repository:
     1. Go to the repository
     2. Find "Download the model" link in their README
     3. Download `best.pt`
   - Place the downloaded `best.pt` in `image_detection/model/` directory
   - If no model is found, the project will automatically download and use YOLOv8n (not recommended for climbing holds)

## Installation

You can set up this project using either Conda (recommended) or standard Python virtual environment.

### Option 1: Using Conda (Recommended)

1. If you haven't installed Conda yet, download and install [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or [Anaconda](https://www.anaconda.com/download).

2. Clone the repository:
   ```bash
   git clone <repository-url>
   cd holdsleuth
   ```

3. Create and activate a new conda environment:
   ```bash
   conda create -n holdsleuth python=3.8
   conda activate holdsleuth
   ```

4. Install PyTorch and other dependencies:
   ```bash
   # Install PyTorch with CUDA support (if you have a NVIDIA GPU)
   conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia

   # Or install CPU-only version
   # conda install pytorch torchvision torchaudio cpuonly -c pytorch

   # Install other dependencies
   conda install -c conda-forge flask numpy opencv pillow pytest ultralytics svgwrite segment-anything
   ```

5. Download required model files:
   - SAM model file (`sam_vit_h_4b8939.pth`) should be placed in the `models/` directory
   - YOLO model file (`best.pt`) should be placed in the `image_detection/model/` directory

### Option 2: Using Python venv (Not Recommended for Deep Learning)

While you can use Python's venv, we recommend using Conda as it handles deep learning dependencies better.

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd holdsleuth
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install required packages:
   ```bash
   pip install torch torchvision torchaudio
   pip install -r requirements.txt
   ```

4. Download required model files as described in the "Required Model Files" section.

## Project Structure

```
HoldSleuth/
├── image_detection/       # Core detection modules
│   ├── sam_blob_extractor.py  # SAM-based shape extraction
│   ├── wall_scanner.py        # Wall scanning utilities
│   ├── yolo_hold_detector.py  # YOLO-based hold detection
│   ├── model/                 # YOLO model directory
│   ├── images/               # Input images directory
│   └── holds_detected/       # Output directory for detections
├── models/                # SAM model directory
├── data/                 # Sample images and test data
├── tests/              # Unit tests
├── docs/               # Additional documentation
├── scripts/            # Utility scripts
└── examples/           # Usage examples
```

## Usage

### Image-based Detection

```python
from image_detection.yolo_hold_detector import YOLOHoldDetector
from image_detection.sam_blob_extractor import SAMBlobExtractor

# Initialize detectors
yolo_detector = YOLOHoldDetector()
sam_extractor = SAMBlobExtractor()

# Detect holds
holds = yolo_detector.detect_holds(image)
blobs = sam_extractor.extract_blobs(image, holds)
```

## Future Plans

1. Real-time Detection
   - Implement video feed processing
   - Optimize for real-time performance
   - Add tracking capabilities

2. 3D Scanning
   - Microsoft Kinect integration
   - 3D hold modeling
   - Depth analysis

3. Additional Features
   - Route generation
   - Difficulty estimation
   - Hold classification by type

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.