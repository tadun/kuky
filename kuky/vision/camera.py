"""USB webcam interface."""

import cv2
import numpy as np


class Camera:
    """Wraps a USB webcam for frame capture."""

    def __init__(self, device_index: int = 0, width: int = 640, height: int = 480, fps: int = 30) -> None:
        self._cap = cv2.VideoCapture(device_index)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self._cap.set(cv2.CAP_PROP_FPS, fps)

        if not self._cap.isOpened():
            raise RuntimeError(f"Cannot open camera at device index {device_index}")

    def read(self) -> np.ndarray:
        """Return the latest BGR frame. Raises RuntimeError on failure."""
        ok, frame = self._cap.read()
        if not ok:
            raise RuntimeError("Failed to capture frame from camera")
        return frame

    def release(self) -> None:
        self._cap.release()

    def __enter__(self) -> "Camera":
        return self

    def __exit__(self, *_) -> None:
        self.release()
