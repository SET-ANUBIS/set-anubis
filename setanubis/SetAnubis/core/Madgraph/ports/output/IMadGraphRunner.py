from abc import ABC, abstractmethod


class IMadGraphRunner(ABC):
    @abstractmethod
    def retrieve_events(self, output_dir="db/Temp/madgraph/Events", width_mode = False):
        pass
    
    @abstractmethod
    def run(self):
        pass
    
    @abstractmethod
    def inject_all_cards(self):
        pass