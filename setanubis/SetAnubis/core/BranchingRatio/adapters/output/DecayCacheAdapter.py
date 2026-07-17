"""Adapter exposing cached UFO decay callables through the database port."""

from SetAnubis.core.BranchingRatio.ports.IDataBaseAdapter import IDataBaseAdapter
from SetAnubis.core.DataBase.adapters.DecayProvider import DecayProvider


class DecayCacheAdapter(IDataBaseAdapter):
    """Load decay-function caches from a trusted UFO directory."""

    def __init__(self, path: str) -> None:
        """Store the UFO directory path."""
        self.path = path

    def get(self):
        """Return the decay function and parameter caches."""
        return DecayProvider(self.path).get_caches()
