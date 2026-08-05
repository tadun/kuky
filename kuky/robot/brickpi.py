"""BrickPi3 motor control interface."""

from typing import Self

from kuky.navigation.navigator import Action, NavDecision

try:
    import brickpi3  # type: ignore
    _BRICKPI_AVAILABLE = True
except ImportError:
    _BRICKPI_AVAILABLE = False


# Motor ports — adjust to match your physical wiring
PORT_LEFT = "PORT_A"
PORT_RIGHT = "PORT_D"

# NXT Ultrasonic Sensor port
PORT_ULTRASONIC = "PORT_1"

# Degrees per second at full speed (tune to your wheels)
MAX_DPS = 300

# Stop motors when ultrasonic reads closer than this (cm)
STOP_DISTANCE_CM = 15.0


class BrickPiRobot:
    """
    Wraps BrickPi3 motor calls so the rest of the system stays hardware-agnostic.

    When BrickPi3 is not installed (e.g. developing on macOS) the class
    runs in dry-run mode and only prints what it would do.
    """

    def __init__(self, dry_run: bool = not _BRICKPI_AVAILABLE) -> None:
        self._dry_run = dry_run
        if not dry_run:
            self._bp = brickpi3.BrickPi3()
            self._left = getattr(self._bp, PORT_LEFT)
            self._right = getattr(self._bp, PORT_RIGHT)
            self._bp.set_motor_limits(self._left, dps=MAX_DPS)
            self._bp.set_motor_limits(self._right, dps=MAX_DPS)
            # Configure NXT ultrasonic sensor
            self._us_port = getattr(self._bp, PORT_ULTRASONIC)
            self._bp.set_sensor_type(
                self._us_port,
                self._bp.SENSOR_TYPE.NXT_ULTRASONIC,
            )
        else:
            print("[BrickPiRobot] dry-run mode — no hardware commands sent")

    def execute(self, decision: NavDecision) -> None:
        """Translate a NavDecision into motor commands."""
        speed = decision.speed
        match decision.action:
            case Action.FORWARD:
                self._set_motors(speed, speed)
            case Action.TURN_LEFT:
                self._set_motors(-speed * 0.5, speed)
            case Action.TURN_RIGHT:
                self._set_motors(speed, -speed * 0.5)
            case Action.REVERSE:
                self._set_motors(-speed, -speed)
            case Action.STOP:
                self._set_motors(0.0, 0.0)

    def stop(self) -> None:
        self._set_motors(0.0, 0.0)

    def read_distance_cm(self) -> float:
        """Return ultrasonic distance in cm, or 999 on dry-run / read error."""
        if self._dry_run:
            return 999.0
        try:
            return float(self._bp.get_sensor(self._us_port))
        except Exception:
            return 999.0

    def _set_motors(self, left: float, right: float) -> None:
        left_dps = int(left * MAX_DPS)
        right_dps = int(right * MAX_DPS)
        if self._dry_run:
            print(f"[motors] left={left_dps} dps  right={right_dps} dps")
            return
        self._bp.set_motor_dps(self._left, left_dps)
        self._bp.set_motor_dps(self._right, right_dps)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_) -> None:
        self.stop()
