import json
from SetAnubis.core.DataBase.ports.IExtractor import IExtractor

class JSONExtractor(IExtractor):
    """Extractor class for loading JSON files."""
    @staticmethod
    def extract(path):
        """Extracts data from a JSON file.

        Args:
            path (str): Path to the JSON file.

        Returns:
            Dict[str, Any]: Data extracted from the JSON file.
        """
        with open(path) as f:
            return json.load(f)
        