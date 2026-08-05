"""YOLOv8-based object detection + instance segmentation for living room awareness."""

from dataclasses import dataclass, field

import cv2
import numpy as np


@dataclass
class Detection:
    label: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int
    # Binary mask resized to the original frame dimensions (H×W bool), or None
    mask: np.ndarray | None = field(default=None, repr=False)

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
    Runs YOLOv8n-seg inference on frames.

    Uses the nano segmentation model by default to keep latency acceptable on a
    Raspberry Pi.  A custom model path can be supplied for fine-tuned weights.
    """

    def __init__(
        self,
        model_path: str = "yolov8n-seg.pt",
        confidence_threshold: float = 0.45,
        relevant_labels: set[str] | None = None,
        device: str = "cpu",
    ) -> None:
        # Lazy import so the module loads on non-Pi machines without ultralytics
        from ultralytics import YOLO  # type: ignore

        self._model = YOLO(model_path)
        self._conf = confidence_threshold
        self._relevant = relevant_labels if relevant_labels is not None else RELEVANT_LABELS
        self._device = device

    def detect(self, frame: np.ndarray) -> list[Detection]:
        """Return detections (with masks) filtered to relevant living room objects."""
        h, w = frame.shape[:2]
        raw = self._model(frame, conf=self._conf, device=self._device, verbose=False)
        detections: list[Detection] = []

        for result in raw:
            from ultralytics.engine.results import Results  # type: ignore
            if not isinstance(result, Results):
                continue
            masks_data = result.masks  # may be None for det-only models
            for idx, box in enumerate(result.boxes or []):
                label = result.names[int(box.cls)]
                if label not in self._relevant:
                    continue
                x1, y1, x2, y2 = (int(v) for v in box.xyxy[0])

                mask: np.ndarray | None = None
                if masks_data is not None and idx < len(masks_data):
                    # masks_data.data is (N, H, W) float tensor on [0,1]
                    mask_arr = np.asarray(masks_data.data[idx].cpu(), dtype=np.float32)  # type: ignore[union-attr]
                    mask = cv2.resize(mask_arr, (w, h)) > 0.5

                detections.append(Detection(
                    label=label,
                    confidence=float(box.conf),
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    mask=mask,
                ))

        return detections


def draw_detections(frame: np.ndarray, detections: list[Detection]) -> np.ndarray:
    """Overlay coloured instance-segmentation masks and bounding boxes onto frame."""
    overlay = frame.copy()

    for det in detections:
        color = _class_color(det.label)

        if det.mask is not None:
            colored = np.zeros_like(frame, dtype=np.uint8)
            colored[det.mask] = color
            overlay = cv2.addWeighted(overlay, 1.0, colored, 0.45, 0)

        cv2.rectangle(overlay, (det.x1, det.y1), (det.x2, det.y2), color, 2)
        label_text = f"{det.label} {det.confidence:.0%}"
        cv2.putText(overlay, label_text, (det.x1, det.y1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

    return overlay


# Deterministic per-class hue using the golden angle so adjacent IDs differ visually
_COLOR_CACHE: dict[str, tuple[int, int, int]] = {}


def _class_color(label: str) -> tuple[int, int, int]:
    if label not in _COLOR_CACHE:
        hue = (hash(label) * 137) % 180
        hsv = np.array([[[hue, 210, 230]]], dtype=np.uint8)
        bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0, 0]
        _COLOR_CACHE[label] = (int(bgr[0]), int(bgr[1]), int(bgr[2]))
    return _COLOR_CACHE[label]

