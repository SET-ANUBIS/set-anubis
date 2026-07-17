"""Port exposing a UFO model as a parameter-expression tree."""

from abc import ABC, abstractmethod

from SetAnubis.core.DataBase.domain.UFOTree import ExpressionTree


class IUFOInterface(ABC):
    """Build and expose the parameter tree parsed from a UFO model."""

    @abstractmethod
    def get_tree(self) -> ExpressionTree:
        """Return the parsed UFO parameter-expression tree."""
        raise NotImplementedError
