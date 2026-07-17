"""Available backends for decay-width and branching-ratio calculations."""

from enum import Enum


class CalculationDecayStrategy(Enum):
    """Select how a decay observable is obtained."""

    CONSTANT = "CONSTANT"
    UFO = "UFO"
    PYTHON = "PYTHON"
    FILE_INTERPOLATION = "FILE_INTERPOLATION"
    MADGRAPH = "MADGRAPH"
    MARTY = "MARTY"
