import pytest
import numpy as np
import cv2
from image_detection.yolo_hold_detector import YOLOHoldDetector, Hold
from image_detection.sam_blob_extractor import SAMBlobExtractor, BlobHold

def test_hold_dataclass():
    """Test Hold dataclass creation"""
    hold = Hold(
        center=(100, 100),
        bbox=(90, 90, 110, 110),
        confidence=0.95,
        color="blue"
    )
    assert hold.center == (100, 100)
    assert hold.bbox == (90, 90, 110, 110)
    assert hold.confidence == 0.95
    assert hold.color == "blue"

def test_blob_hold_dataclass():
    """Test BlobHold dataclass creation"""
    dummy_contour = np.array([[[0, 0]], [[0, 1]], [[1, 1]], [[1, 0]]])
    dummy_mask = np.zeros((10, 10), dtype=np.uint8)
    dummy_hull = np.array([[[0, 0]], [[0, 1]], [[1, 1]], [[1, 0]]])
    dummy_min_rect = ((0.5, 0.5), (1.0, 1.0), 0.0)

    blob = BlobHold(
        center=(5, 5),
        contour=dummy_contour,
        area=100.0,
        color="yellow",
        confidence=0.9,
        mask=dummy_mask,
        convex_hull=dummy_hull,
        min_rect=dummy_min_rect
    )
    
    assert blob.center == (5, 5)
    assert np.array_equal(blob.contour, dummy_contour)
    assert blob.area == 100.0
    assert blob.color == "yellow"
    assert blob.confidence == 0.9
    assert np.array_equal(blob.mask, dummy_mask)
    assert np.array_equal(blob.convex_hull, dummy_hull)
    assert blob.min_rect == dummy_min_rect 