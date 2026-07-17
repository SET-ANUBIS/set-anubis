"""Port for file-backed decay-width interpolation."""

from typing import Dict, List, Set


class IFileInterpolationSubStrategy:
    """Load tabulated decay data and interpolate a requested channel."""

    def load_file(self, file_path: str, varying_params: List[str]) -> None:
        """Load tabulated values and record the parameters varied by the table."""
        raise NotImplementedError

    def interpolate(
        self,
        mother: int,
        daughters: Set[int],
        param_values: Dict[str, float],
    ) -> float:
        """Interpolate the value for a decay channel at ``param_values``."""
        raise NotImplementedError
