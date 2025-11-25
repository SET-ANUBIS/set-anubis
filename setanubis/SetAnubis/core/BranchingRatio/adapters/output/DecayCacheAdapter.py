

from SetAnubis.core.DataBase.adapters.DecayProvider import DecayProvider
from SetAnubis.core.BranchingRatio.ports.IDataBaseAdapter import IDataBaseAdapter

class DecayCacheAdapter(IDataBaseAdapter):

    def __init__(self, path):
        self.path = path
    def get(self):
        return DecayProvider(self.path).get_caches()