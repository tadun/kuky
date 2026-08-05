"""Living room navigation logic."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

from kuky.vision.obstacle_detection import ObstacleMap
from kuky.vision.object_detection import Detection


class Action(Enum):
    FORWARD = auto()
    TURN_LEFT = auto()
    TURN_RIGHT = auto()
    STOP = auto()
    REVERSE = auto()


@dataclass
class NavDecision:
    action: Action
    reason: str
    speed: float = 0.5   # 0.0 – 1.0


# Edge density above this triggers avoidance
OBSTACLE_THRESHOLD = 0.12

# A person this close (fraction of frame width from centre) triggers stop
PERSON_CLOSE_THRESHOLD = 0.65


class Navigator:
    """
    Combines obstacle map and object detections into a driving action.

    Priority order:
      1. Stop if a person is very close (safety first)
      2. Avoid edges/obstacles detected by classical CV
      3. Steer away from detected objects when they are centred
      4. Otherwise go forward
    """

    def __init__(
        self,
        obstacle_threshold: float = OBSTACLE_THRESHOLD,
        person_threshold: float = PERSON_CLOSE_THRESHOLD,
        frame_width: int = 640,
    ) -> None:
        self._obs_thresh = obstacle_threshold
        self._person_thresh = person_threshold
        self._frame_width = frame_width

    def decide(
        self,
        obstacle_map: ObstacleMap,
        detections: Optional[list[Detection]] = None,
    ) -> NavDecision:
        if detections:
            for det in detections:
                if det.label == "person":
                    norm_x = det.centre_x / self._frame_width
                    box_width_fraction = (det.x2 - det.x1) / self._frame_width
                    if box_width_fraction > self._person_thresh:
                        return NavDecision(Action.STOP, "person too close", speed=0.0)
                    # Steer away from person
                    if norm_x < 0.4:
                        return NavDecision(Action.TURN_RIGHT, "person on left", speed=0.35)
                    if norm_x > 0.6:
                        return NavDecision(Action.TURN_LEFT, "person on right", speed=0.35)

        centre = obstacle_map.centre
        left = obstacle_map.left
        right = obstacle_map.right

        if centre > self._obs_thresh:
            if left < right:
                return NavDecision(Action.TURN_LEFT, f"centre blocked ({centre:.2f}), left clearer", speed=0.4)
            return NavDecision(Action.TURN_RIGHT, f"centre blocked ({centre:.2f}), right clearer", speed=0.4)

        if left > self._obs_thresh and right > self._obs_thresh:
            return NavDecision(Action.REVERSE, "both sides blocked", speed=0.3)

        if left > self._obs_thresh:
            return NavDecision(Action.TURN_RIGHT, f"left blocked ({left:.2f})", speed=0.4)

        if right > self._obs_thresh:
            return NavDecision(Action.TURN_LEFT, f"right blocked ({right:.2f})", speed=0.4)

        return NavDecision(Action.FORWARD, "path clear", speed=0.5)
