from pathlib import Path

class MadGraphWidthCard:
    """Class to generate width calculation cards for MadGraph simulations.

    Attributes:
        ufo_path (Path): Path to the UFO model directory.
        particles (list[str]): List of particle identifiers for width calculations.
    """
    def __init__(self, ufo_path : str, particles):
        """Initializes MadGraphWidthCard with model path and particles.

        Args:
            ufo_path (str): Path to the UFO model.
            particles (list[str]): List of particle identifiers.
        """
        self.ufo_path = ufo_path
        self.particles = particles

    def generate(self) -> str:
        """Generates the content for the width calculation card.

        Returns:
            str: Content of the width calculation card.
        """
        model_name = Path(self.ufo_path).name
        lines = [
            "import model sm",
            f"import model {model_name}",
        ]
        for p in self.particles:
            lines.append(f"compute_width {p}")
        return "\n".join(lines)
