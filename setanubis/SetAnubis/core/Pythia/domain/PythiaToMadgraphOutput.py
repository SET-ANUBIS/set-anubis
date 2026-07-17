"""Convert text and HepMC scan outputs into a MadGraph-style run layout."""

from __future__ import annotations

import logging
import re
import shutil
from collections.abc import Callable
from pathlib import Path

LOGGER = logging.getLogger(__name__)


class ScanProcessor:
    """Collect scan metadata and event files into numbered run directories."""

    def __init__(
        self,
        text_dir: Path,
        hepmc_dir: Path,
        output_dir: Path,
        param_names: list[str],
        param_info_func: Callable[[str], tuple[str, str]],
        scan_filename: str = "scan_run_output.txt",
        particle_id: str | int | None = None,
    ) -> None:
        """Configure the scan conversion and initialise its summary file."""
        self.text_dir = Path(text_dir)
        self.hepmc_dir = Path(hepmc_dir)
        self.output_dir = Path(output_dir)
        self.param_names = list(param_names)
        self.param_info_func = param_info_func
        self.scan_filename = scan_filename
        self.particle_id = str(particle_id) if particle_id is not None else None
        self.scan_path = self.output_dir / self.scan_filename
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._initialize_scan_file()

    def _initialize_scan_file(self) -> None:
        parts = []
        for param in self.param_names:
            label, unit = self.param_info_func(param)
            parts.append(f"{label}#{unit}")
        width_label = (
            f"width#{self.particle_id}" if self.particle_id else "width#first_DECAY"
        )
        parts.extend(["cross", width_label])
        header = "#run_name            " + "    ".join(
            f"{part:<20}" for part in parts
        )
        self.scan_path.write_text(header + "\n", encoding="utf-8")
        LOGGER.info("Scan file initialized: %s", self.scan_path)

    @staticmethod
    def _extract_float(value: str) -> float | None:
        """Decode a filename-safe floating-point value such as ``1p5e-3``."""
        try:
            return float(value.replace("p", "."))
        except ValueError:
            return None

    def _parse_filename(self, filename: str) -> dict[str, float] | None:
        """Extract all configured scan parameters from a result filename."""
        values: dict[str, float] = {}
        number = r"([+-]?(?:\d+(?:[p.]\d*)?|[p.]\d+)(?:[eE][+-]?\d+)?)"

        for param in self.param_names:
            match = re.search(rf"{re.escape(param)}{number}", filename)
            if not match:
                LOGGER.warning("Parameter %s is missing from %s", param, filename)
                return None
            value = self._extract_float(match.group(1))
            if value is None:
                LOGGER.warning("Could not parse %s from %s", param, filename)
                return None
            values[param] = value

        return values

    def _parse_text_file(self, filepath: Path) -> tuple[float, float]:
        """Read a cross section and particle width from one text output."""
        cross = 0.0
        width = 0.0
        decay_pattern = (
            rf"^\s*DECAY\s+{re.escape(self.particle_id)}\s+([\deE+\-.]+)"
            if self.particle_id
            else r"^\s*DECAY\s+[-]?\d+\s+([\deE+\-.]+)"
        )

        try:
            lines = filepath.read_text(encoding="utf-8").splitlines()
            for line in lines:
                if "Integrated weight" in line:
                    cross = float(line.split(":", 1)[1].strip())
                elif "Pythia sigmaGen" in line and cross == 0.0:
                    cross = float(line.split(":", 1)[1].strip())
                match = re.match(decay_pattern, line)
                if match:
                    width = float(match.group(1))
                    if self.particle_id is None:
                        break
        except (OSError, ValueError, IndexError) as exc:
            LOGGER.error("Could not read file %s: %s", filepath, exc)
        return cross, width

    def _copy_hepmc_file(self, base_filename: str, target_dir: Path) -> None:
        """Copy the matching HepMC event file into a numbered run directory."""
        source = self.hepmc_dir / f"{base_filename}.hepmc"
        destination = target_dir / "event.hepmc"
        if source.exists():
            shutil.copy2(source, destination)
        else:
            LOGGER.warning("Missing HepMC file: %s", source)

    def process_all(self) -> None:
        """Convert every valid text result and its matching HepMC file."""
        run_counter = 1
        for text_file in sorted(self.text_dir.glob("*.txt")):
            parsed_params = self._parse_filename(text_file.name)
            if parsed_params is None:
                continue

            cross, width = self._parse_text_file(text_file)
            run_name = f"run_{run_counter:02d}"
            run_dir = self.output_dir / run_name
            run_dir.mkdir(parents=True, exist_ok=True)
            self._copy_hepmc_file(text_file.stem, run_dir)

            with self.scan_path.open("a", encoding="utf-8") as output:
                line = f"{run_name:<20}"
                for param in self.param_names:
                    line += f"{parsed_params[param]:<20.6e}"
                line += f"{cross:<20.6e}{width:<20.6e}\n"
                output.write(line)
            run_counter += 1

        LOGGER.info("Conversion complete. Files are available in: %s", self.output_dir)


def example_param_info(param: str) -> tuple[str, str]:
    """Return labels and units used by the built-in scan example."""
    mapping = {
        "mass": ("mass", "particle"),
        "coupling": ("coupling", "arb"),
    }
    return mapping.get(param, (param, "?"))
