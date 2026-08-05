"""Tests for obstacle detection."""

import numpy as np
import pytest

from kuky.vision.obstacle_detection import ObstacleDetector, ObstacleMap


def _solid_frame(h: int = 480, w: int = 640, color: tuple = (100, 100, 100)) -> np.ndarray:
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    frame[:] = color
    return frame


def _edge_frame(h: int = 480, w: int = 640) -> np.ndarray:
    """Frame with a sharp vertical edge in the centre zone."""
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    frame[:, w // 3 : w * 2 // 3] = 255
    return frame


def test_clear_frame_has_low_density():
    detector = ObstacleDetector()
    result = detector.detect(_solid_frame())
    assert result.left < 0.05
    assert result.centre < 0.05
    assert result.right < 0.05


def test_edge_frame_raises_centre_density():
    detector = ObstacleDetector()
    result = detector.detect(_edge_frame())
    assert result.centre > result.left
    assert result.centre > result.right


def test_returns_obstacle_map():
    detector = ObstacleDetector()
    result = detector.detect(_solid_frame())
    assert isinstance(result, ObstacleMap)
    assert result.raw_edges is not None
