from abc import ABC, abstractmethod

class IMadGraphPort(ABC):
    """
    Port interface for executing and retrieving MadGraph simulation results.

    This defines the expected behaviors for any external MadGraph integration
    (e.g., via Docker, local execution, cloud job manager).
    """

    @abstractmethod
    def run(self) -> None:
        """
        Executes the configured MadGraph job.
        """
        pass

    @abstractmethod
    def retrieve_events(self, output_path: str) -> None:
        """
        Retrieves the generated event files from the execution environment.

        Args:
            output_path (str): Path to store the Events folder locally.
        """
        pass
