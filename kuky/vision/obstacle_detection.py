"""Classical OpenCV obstacle detection using optical flow and edge analysis."""

from dataclasses import dataclass, field
import cv2
import numpy as np


@dataclass
class ObstacleMap:
    """Encodes where obstacles are in the frame (left / centre / right zones)."""
    left: float = 0.0    # 0.0 = clear, 1.0 = fully blocked
    centre: float = 0.0
    right: float = 0.0
    raw_edges: np.ndarray = field(default=None, repr=False)


class ObstacleDetector:
    """
    Detects obstacles using Canny edges + column density analysis.

    Divides the lower half of the frame into three vertical zones and
    scores each zone by edge density — a high score means more edges
    (likely an obstacle).
    """

    def __init__(
        self,
        canny_low: int = 50,
        canny_high: int = 150,
        roi_top_fraction: float = 0.4,  # ignore top 40 % (ceiling / sky)
    ) -> None:
        self._canny_low = canny_low
        self._canny_high = canny_high
        self._roi_top = roi_top_fraction

    def detect(self, frame: np.ndarray) -> ObstacleMap:
        h, w = frame.shape[:2]
        roi_y = int(h * self._roi_top)
        roi = frame[roi_y:, :]

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, self._canny_low, self._canny_high)

        third = w // 3
        left_density = edges[:, :third].mean() / 255.0
        centre_density = edges[:, third : third * 2].mean() / 255.0
        right_density = edges[:, third * 2 :].mean() / 255.0

        return ObstacleMap(
            left=float(left_density),
            centre=float(centre_density),
            right=float(right_density),
            raw_edges=edges,
        )
