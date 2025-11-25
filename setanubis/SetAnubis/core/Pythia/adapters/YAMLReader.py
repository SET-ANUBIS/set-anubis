from SetAnubis.core.DataBase.adapters.YAMLParser import YAMLParser
from pathlib import Path

class YamlReader:
    """Utility class for reading YAML files using database adapters."""
    @staticmethod
    def get(file_path : Path):
        """Reads YAML file using database YAMLReader.

        Args:
            file_path (str): Path to the YAML file.

        Returns:
            Dict[str, Any]: Parsed data from the YAML file.

        Raises:
            FileNotFoundError: If the file does not exist.
            yaml.YAMLError: If parsing errors occur.
        """
        return YAMLParser.parse(file_path)