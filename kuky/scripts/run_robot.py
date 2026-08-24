"""Main entry point — runs the vision-navigation loop and HTTP/WebSocket server."""

import argparse
import asyncio
import logging
import signal
import time

import cv2

from kuky.vision.camera import Camera
from kuky.vision.obstacle_detection import ObstacleDetector
from kuky.vision.object_detection import ObjectDetector, draw_detections
from kuky.navigation.navigator import Navigator, Action, NavDecision
from kuky.robot.brickpi import BrickPiRobot, STOP_DISTANCE_CM
from kuky.server.app import RobotServer

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Kuky living room navigation")
    p.add_argument("--camera", type=int, default=0, help="Camera device index")
    p.add_argument("--model", default="yolov8n-seg.pt", help="YOLOv8 seg model weights")
    p.add_argument("--conf", type=float, default=0.45, help="Detection confidence threshold")
    p.add_argument("--dry-run", action="store_true", help="Print motor commands, don't move")
    p.add_argument("--port", type=int, default=8765, help="Server port")
    p.add_argument("--fps-limit", type=float, default=5.0, help="Max inference FPS")
    return p.parse_args()


async def main() -> None:
    args = parse_args()
    frame_interval = 1.0 / args.fps_limit

    obstacle_detector = ObstacleDetector()
    object_detector = ObjectDetector(model_path=args.model, confidence_threshold=args.conf)
    navigator = Navigator()
    server = RobotServer(port=args.port)

    loop = asyncio.get_running_loop()
    running = True

    def _shutdown(sig, _frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    await server.start()

    with Camera(device_index=args.camera) as cam, BrickPiRobot(dry_run=args.dry_run) as robot:
        log.info("Kuky started — connect at http://kuky.local:%d/stream", args.port)
        last_time = 0.0

        while running:
            now = time.monotonic()
            if now - last_time < frame_interval:
                await asyncio.sleep(0.005)
                continue
            last_time = now

            # Run blocking calls in the thread pool so asyncio stays responsive
            frame = await loop.run_in_executor(None, cam.read)
            obstacles = await loop.run_in_executor(None, obstacle_detector.detect, frame)
            detections = await loop.run_in_executor(None, object_detector.detect, frame)

            # Ultrasonic overrides everything when obstacle is very close
            distance = await loop.run_in_executor(None, robot.read_distance_cm)

            if server.mode == "manual":
                decision = _manual_decision(server.manual_dir, server.manual_speed)
            else:
                decision = navigator.decide(obstacles, detections)

            # Hard stop if ultrasonic detects imminent collision
            if distance < STOP_DISTANCE_CM and decision.action in (
                Action.FORWARD, Action.TURN_LEFT, Action.TURN_RIGHT
            ):
                decision = NavDecision(Action.STOP, f"ultrasonic: {distance:.0f} cm", speed=0.0)

            await loop.run_in_executor(None, robot.execute, decision)

            # Build annotated frame and push to stream
            annotated = draw_detections(frame, detections)
            _draw_hud(annotated, decision, distance, server.mode)
            _, jpeg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 75])
            server.push_jpeg(jpeg.tobytes())

            await server.broadcast_telemetry({
                "mode": server.mode,
                "action": decision.action.name,
                "reason": decision.reason,
                "distance_cm": round(distance, 1),
            })

    log.info("Kuky stopped.")


def _manual_decision(direction: str, speed: float = 1.0) -> NavDecision:
    match direction:
        case "forward":  return NavDecision(Action.FORWARD,    "manual", speed=speed)
        case "backward": return NavDecision(Action.REVERSE,    "manual", speed=speed)
        case "left":     return NavDecision(Action.TURN_LEFT,  "manual", speed=speed * 0.8)
        case "right":    return NavDecision(Action.TURN_RIGHT, "manual", speed=speed * 0.8)
        case _:          return NavDecision(Action.STOP,       "manual", speed=0.0)


def _draw_hud(frame: cv2.typing.MatLike, decision: NavDecision,
              distance: float, mode: str) -> None:
    h, w = frame.shape[:2]
    cv2.putText(frame, f"[{mode.upper()}] {decision.action.name}: {decision.reason}",
                (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 200, 255), 2, cv2.LINE_AA)
    dist_color = (0, 60, 255) if distance < STOP_DISTANCE_CM * 2 else (0, 220, 0)
    cv2.putText(frame, f"dist: {distance:.0f} cm",
                (10, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.65, dist_color, 2, cv2.LINE_AA)


if __name__ == "__main__":
    asyncio.run(main())

