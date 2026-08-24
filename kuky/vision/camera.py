"""USB webcam interface."""

from typing import Self

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

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_) -> None:
        self.release()


class MockCamera:
    """Synthetic frame source for offline development; no hardware required."""

    def __init__(
        self,
        width: int = 640,
        height: int = 480,
        pattern: str = "checkerboard",  # "checkerboard" | "gradient" | "solid"
    ) -> None:
        self._w = width
        self._h = height
        self._pattern = pattern
        self._frame_index = 0

    def read(self) -> np.ndarray:
        frame = self._make_frame()
        self._frame_index += 1
        return frame

    def _make_frame(self) -> np.ndarray:
        match self._pattern:
            case "gradient":
                col = np.linspace(0, 255, self._w, dtype=np.uint8)
                return np.tile(col, (self._h, 1, 3)).reshape(self._h, self._w, 3)
            case "solid":
                return np.full((self._h, self._w, 3), 128, dtype=np.uint8)
            case _:  # checkerboard — shifts one pixel per frame so motion-based code sees change
                size = 40
                r = np.arange(self._h)[:, None]
                c = np.arange(self._w)[None, :]
                checker = (((r // size) + (c // size)) % 2 * 200).astype(np.uint8)
                frame = np.stack([checker, checker, checker], axis=-1)
                return np.roll(frame, self._frame_index % size, axis=1)

    def release(self) -> None:
        pass

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_) -> None:
        self.release()
