"""Main entry point — runs the vision-navigation loop on the robot."""

import argparse
import signal
import sys
import time

import cv2

from kuky.vision.camera import Camera
from kuky.vision.obstacle_detection import ObstacleDetector
from kuky.vision.object_detection import ObjectDetector
from kuky.navigation.navigator import Navigator
from kuky.robot.brickpi import BrickPiRobot


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Kuky living room navigation")
    p.add_argument("--camera", type=int, default=0, help="Camera device index")
    p.add_argument("--model", default="yolov8n.pt", help="YOLOv8 model weights")
    p.add_argument("--conf", type=float, default=0.45, help="Detection confidence threshold")
    p.add_argument("--dry-run", action="store_true", help="Print motor commands, don't move")
    p.add_argument("--show", action="store_true", help="Display live debug window (requires display)")
    p.add_argument("--fps-limit", type=float, default=10.0, help="Max inference FPS to reduce CPU load")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    frame_interval = 1.0 / args.fps_limit

    obstacle_detector = ObstacleDetector()
    object_detector = ObjectDetector(model_path=args.model, confidence_threshold=args.conf)
    navigator = Navigator()

    running = True

    def _shutdown(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    with Camera(device_index=args.camera) as cam, BrickPiRobot(dry_run=args.dry_run) as robot:
        print("Kuky started — press Ctrl+C to stop")
        last_time = 0.0

        while running:
            now = time.monotonic()
            if now - last_time < frame_interval:
                time.sleep(0.005)
                continue
            last_time = now

            frame = cam.read()
            obstacles = obstacle_detector.detect(frame)
            detections = object_detector.detect(frame)
            decision = navigator.decide(obstacles, detections)

            robot.execute(decision)
            print(f"[nav] {decision.action.name:12s} | {decision.reason}")

            if args.show:
                _draw_debug(frame, obstacles, detections, decision)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    if args.show:
        cv2.destroyAllWindows()
    print("Kuky stopped.")


def _draw_debug(frame, obstacles, detections, decision) -> None:
    import numpy as np
    h, w = frame.shape[:2]

    for det in detections:
        cv2.rectangle(frame, (det.x1, det.y1), (det.x2, det.y2), (0, 255, 0), 2)
        cv2.putText(frame, f"{det.label} {det.confidence:.2f}",
                    (det.x1, det.y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    cv2.putText(frame, f"{decision.action.name}: {decision.reason}",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 120, 255), 2)

    # Edge density bars at the bottom
    bar_h = 20
    third = w // 3
    for i, (density, label) in enumerate([(obstacles.left, "L"), (obstacles.centre, "C"), (obstacles.right, "R")]):
        x = i * third
        fill = int(density * third)
        cv2.rectangle(frame, (x, h - bar_h), (x + fill, h), (0, 0, 255), -1)
        cv2.putText(frame, f"{label}:{density:.2f}", (x + 4, h - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    cv2.imshow("Kuky", frame)


if __name__ == "__main__":
    main()
