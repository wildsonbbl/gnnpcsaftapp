"""Dataclasses for filling UI inputs."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class BinaryFillRequest:
    """Input values for filling binary mixture fields."""

    pressure: Optional[float] = None
    t_min: Optional[float] = None
    t_max: Optional[float] = None
    x1: Optional[float] = None
    kij: Optional[float] = None


@dataclass
class TernaryFillRequest:
    """Input values for filling ternary mixture fields."""

    pressure: Optional[float] = None
    t_min: Optional[float] = None
    t_max: Optional[float] = None
    x1: Optional[float] = None
    x2: Optional[float] = None
