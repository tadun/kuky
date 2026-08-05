"""Tests for the navigation decision logic."""

import pytest

from kuky.navigation.navigator import Action, Navigator
from kuky.vision.obstacle_detection import ObstacleMap


def _map(left=0.0, centre=0.0, right=0.0) -> ObstacleMap:
    return ObstacleMap(left=left, centre=centre, right=right)


def test_clear_path_goes_forward():
    nav = Navigator()
    decision = nav.decide(_map())
    assert decision.action == Action.FORWARD


def test_centre_blocked_turns():
    nav = Navigator()
    decision = nav.decide(_map(centre=0.5, left=0.3, right=0.1))
    assert decision.action == Action.TURN_RIGHT   # right is clearer


def test_both_sides_blocked_reverses():
    nav = Navigator()
    decision = nav.decide(_map(left=0.5, centre=0.5, right=0.5))
    assert decision.action == Action.REVERSE


def test_person_very_close_stops():
    from kuky.vision.object_detection import Detection
    nav = Navigator(frame_width=640)
    big_person = Detection(label="person", confidence=0.9, x1=10, y1=0, x2=430, y2=480)
    decision = nav.decide(_map(), detections=[big_person])
    assert decision.action == Action.STOP
