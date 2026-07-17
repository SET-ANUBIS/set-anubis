"""Unit tests for geometry conversion helpers."""

from __future__ import annotations

import math

import pytest

from SetAnubis.core.Geometry.domain.utils import eta_to_theta, extract_xyz


def test_eta_to_theta_matches_expected_limits_and_symmetry():
    assert eta_to_theta(0.0) == pytest.approx(math.pi / 2)
    assert eta_to_theta(2.0) < math.pi / 2
    assert eta_to_theta(-2.0) > math.pi / 2
    assert eta_to_theta(2.0) + eta_to_theta(-2.0) == pytest.approx(math.pi)


def test_extract_xyz_accepts_three_or_four_components():
    assert extract_xyz((1, 2, 3)) == (1.0, 2.0, 3.0)
    assert extract_xyz([1.5, 2.5, 3.5, 99]) == (1.5, 2.5, 3.5)
