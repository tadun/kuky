"""Tests for BrickPiRobot speed ramping."""

import pytest

from kuky.robot.brickpi import BrickPiRobot, RAMP_STEP, _ramp
from kuky.navigation.navigator import Action, NavDecision


def test_ramp_advances_by_step():
    assert _ramp(0.0, 1.0, 0.2) == pytest.approx(0.2)


def test_ramp_snaps_when_within_step():
    assert _ramp(0.85, 1.0, 0.2) == pytest.approx(1.0)


def test_ramp_decelerates():
    assert _ramp(0.5, 0.0, 0.2) == pytest.approx(0.3)


def test_stop_resets_current_speeds():
    robot = BrickPiRobot(dry_run=True)
    robot._current_left = 0.8
    robot._current_right = 0.6
    robot.stop()
    assert robot._current_left == 0.0
    assert robot._current_right == 0.0


def test_execute_stop_is_immediate():
    robot = BrickPiRobot(dry_run=True)
    robot._current_left = 0.9
    robot._current_right = 0.9
    robot.execute(NavDecision(Action.STOP, "test", speed=0.0))
    assert robot._current_left == 0.0
    assert robot._current_right == 0.0


def test_execute_forward_ramps_not_jumps():
    robot = BrickPiRobot(dry_run=True)
    robot.execute(NavDecision(Action.FORWARD, "test", speed=1.0))
    assert 0.0 < robot._current_left <= RAMP_STEP + 1e-9
    assert 0.0 < robot._current_right <= RAMP_STEP + 1e-9
