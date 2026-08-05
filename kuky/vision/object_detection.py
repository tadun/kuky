"""YOLOv8-based object detection for living room awareness."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np


@dataclass
class Detection:
    label: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def centre_x(self) -> int:
        return (self.x1 + self.x2) // 2

    @property
    def centre_y(self) -> int:
        return (self.y1 + self.y2) // 2


# Living room objects worth tracking for navigation
RELEVANT_LABELS = {
    "person", "chair", "couch", "dining table", "tv",
    "laptop", "dog", "cat", "bottle", "cup",
}


class ObjectDetector:
    """
    Runs YOLOv8n inference on frames.

    Uses the nano model by default to keep latency acceptable on a
    Raspberry Pi.  A custom model path can be supplied for fine-tuned
    living-room weights.
    """

    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        confidence_threshold: float = 0.45,
        relevant_labels: Optional[set[str]] = None,
        device: str = "cpu",
    ) -> None:
        # Lazy import so the module loads on non-Pi machines without ultralytics
        from ultralytics import YOLO  # type: ignore

        self._model = YOLO(model_path)
        self._conf = confidence_threshold
        self._relevant = relevant_labels if relevant_labels is not None else RELEVANT_LABELS
        self._device = device

    def detect(self, frame: np.ndarray) -> list[Detection]:
        """Return detections filtered to relevant living room objects."""
        results = self._model(frame, conf=self._conf, device=self._device, verbose=False)
        detections: list[Detection] = []

        for result in results:
            for box in result.boxes:
                label = result.names[int(box.cls)]
                if label not in self._relevant:
                    continue
                x1, y1, x2, y2 = (int(v) for v in box.xyxy[0])
                detections.append(
                    Detection(
                        label=label,
                        confidence=float(box.conf),
                        x1=x1, y1=y1, x2=x2, y2=y2,
                    )
                )

        return detections
