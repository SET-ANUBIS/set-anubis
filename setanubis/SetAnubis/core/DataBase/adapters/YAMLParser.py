import yaml
from typing import Dict, Any
from SetAnubis.core.DataBase.ports.IParser import IParser

class YAMLParser(IParser):
    """Utility class for reading and parsing YAML files. Inherite from port IParser"""

    @staticmethod
    def parse(file_path: str) -> Dict[str, Any]:
        """Reads YAML file and parses its content.

        Args:
            file_path (str): Path to the YAML file.

        Returns:
            Dict[str, Any]: Parsed data from the YAML file.

        Raises:
            FileNotFoundError: If the file does not exist.
            yaml.YAMLError: If parsing errors occur.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise
        except yaml.YAMLError as exc:
            raise

