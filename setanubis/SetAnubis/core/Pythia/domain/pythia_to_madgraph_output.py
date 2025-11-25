import re
import shutil
import logging
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


import re
import shutil
import logging
from pathlib import Path
from typing import Optional, Callable

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class ScanProcessor:
    def __init__(
        self,
        text_dir: Path,
        hepmc_dir: Path,
        output_dir: Path,
        param_names: list[str],
        param_info_func: Callable[[str], tuple[str, str]],
        scan_filename: str = "scan_run_output.txt",
        particle_id: str = "9900012"
    ):
        self.text_dir = text_dir
        self.hepmc_dir = hepmc_dir
        self.output_dir = output_dir
        self.param_names = param_names
        self.param_info_func = param_info_func
        self.scan_filename = scan_filename
        self.particle_id = particle_id
        self.scan_path = self.output_dir / self.scan_filename
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._initialize_scan_file()

    def _initialize_scan_file(self) -> None:
        parts = []
        for param in self.param_names:
            label, unit = self.param_info_func(param)
            parts.append(f"{label}#{unit}")
        parts.extend([
            "cross", f"width#{self.particle_id}"
        ])
        header = "#run_name            " + "    ".join(f"{p:<20}" for p in parts) + "\n"
        self.scan_path.write_text(header)
        logging.info(f"Fichier de scan initialisé : {self.scan_path}")

    def _extract_float(self, val: str) -> Optional[float]:
        val = val.replace("p", ".")
        try:
            return float(val)
        except ValueError:
            return None

    def _parse_filename(self, filename: str) -> Optional[dict[str, float]]:
        values = {}

        for param in self.param_names:
            match = re.search(rf"{param}([\de\-p]+)", filename)
            if not match:
                logging.warning(f"Paramètre {param} manquant dans : {filename}")
                return None
            value = self._extract_float(match.group(1))
            if value is None:
                logging.warning(f"Erreur de parsing pour {param} dans : {filename}")
                return None
            values[param] = value

        return values

    def _parse_text_file(self, filepath: Path) -> tuple[float, float]:
        cross = 0.0
        width = 0.0

        try:
            for line in filepath.read_text().splitlines():
                if "Integrated weight" in line:
                    cross = float(line.split(":")[1].strip())
                if match := re.match(rf"^\s*DECAY\s+{self.particle_id}\s+([\deE\+\-\.]+)", line):
                    width = float(match.group(1))
        except Exception as e:
            logging.error(f"Erreur lecture fichier {filepath}: {e}")
        return cross, width

    def _copy_hepmc_file(self, base_filename: str, target_dir: Path) -> None:
        src = self.hepmc_dir / f"{base_filename}.hepmc"
        dst = target_dir / "event.hepmc"
        if src.exists():
            shutil.copy(src, dst)
        else:
            logging.warning(f"Fichier HEPMC manquant : {src}")

    def process_all(self) -> None:
        txt_files = sorted(self.text_dir.glob("*.txt"))
        run_counter = 1

        for txt_file in txt_files:
            parsed_params = self._parse_filename(txt_file.name)
            if parsed_params is None:
                continue

            cross, width = self._parse_text_file(txt_file)

            run_name = f"run_{run_counter:02d}"
            run_dir = self.output_dir / run_name
            run_dir.mkdir(parents=True, exist_ok=True)

            self._copy_hepmc_file(txt_file.stem, run_dir)

            with self.scan_path.open("a") as f_out:
                line = f"{run_name:<20}"
                for param in self.param_names:
                    line += f"{parsed_params[param]:<20.6e}"
                line += f"{cross:<20.6e}{width:<20.6e}\n"
                f_out.write(line)

            run_counter += 1

        logging.info(f"Conversion terminée. Fichiers disponibles dans : {self.output_dir}")

def truc(param: str) -> tuple[str, str]:
    # Simule un dictionnaire d'étiquettes et unités
    mapping = {
        "mN1": ("mass", "9900012"),
        "VeN1": ("numixing", "1"),
        "UN1": ("universal", "arb")
    }
    return mapping.get(param, (param, "?"))


if __name__ == "__main__":
    processor = ScanProcessor(
        text_dir=Path("/home/theo/.../text"),
        hepmc_dir=Path("/home/theo/.../hepmc"),
        output_dir=Path("SS_output"),
        param_names=["mN1", "VeN1"],  # ou ["mN1", "VeN1", "UN1"]
        param_info_func=truc,
        scan_filename="scan_run_output.txt",
        particle_id="9900012"
    )
    processor.process_all()