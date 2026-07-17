"""Output port for MadGraph execution backends."""

from abc import ABC, abstractmethod
from os import PathLike


class IMadGraphRunner(ABC):
    """Inject generated cards, execute MadGraph and retrieve its outputs."""

    @abstractmethod
    def retrieve_events(
        self,
        output_dir: str | PathLike[str] = "db/Temp/madgraph/Events",
        width_mode: bool = False,
    ) -> None:
        """Copy generated events or width artefacts to ``output_dir``."""
        raise NotImplementedError

    @abstractmethod
    def run(
        self,
        jobscript: str,
        run_card: str,
        param_card: str,
        pythia_card: str | None,
        madspin_card: str | None,
    ) -> None:
        """Inject all cards and execute the configured MadGraph backend."""
        raise NotImplementedError

    @abstractmethod
    def inject_all_cards(
        self,
        jobscript: str,
        run_card: str,
        param_card: str,
        pythia_card: str | None,
        madspin_card: str | None,
    ) -> None:
        """Write generated cards to the backend execution environment."""
        raise NotImplementedError
