from pathlib import Path
from SetAnubis.core.BranchingRatio.adapters.output.MartyFileCopyBuilder import MartyFileCopyBuilder

class CopyManager:
    def __init__(self, ampli_name: str, builder : MartyFileCopyBuilder):
        self.ampli_name = ampli_name
        self.root = Path(__file__).resolve()
        for _ in range(6):
            self.root = self.root.parent
        self.template_dir = self.root / "Assets" / "MARTY" / "templates"
        self.target_base = self.root / "Assets" / "MARTY" / "MartyTemp" / "libs" / ampli_name
        self.builder = builder

    def prepare_files(self):
        files_to_copy = [
            "integration.cpp",
            "kinematics.cpp",
            "kinematics.h",
            "integration.h",
            "csv_helper.cpp",
            "csv_helper.h"
        ]

        for file_name in files_to_copy:
            src = self.template_dir / file_name
            is_header = file_name.endswith(".h")
            dest_dir = self.target_base / ("include" if is_header else "src")
            dest = dest_dir / file_name

            modifications = []
            if file_name == "kinematics.h":
                modifications.append(("using namespace decay_widths;", f"using namespace {self.ampli_name};"))
            elif file_name == "integration.h":
                modifications.append(("using namespace decay_widths;", f"using namespace {self.ampli_name};"))

            self.builder.add_file(src, dest, modifications)

        makefile_path = self.target_base / "Makefile"
        makefile_modifications = [
            ("CXXSTD  = -std=c++17", "CXXSTD  = -std=c++20")
        ]
        self.builder.add_file(makefile_path, makefile_path, makefile_modifications)

    def write_file(self, cpp_code: str, cpp_path, force: bool = False):
        """
        Prend le contenu du template modifié, génère le fichier C++.

        Args:
            cpp_code (str): Le code C++ à écrire.
            cpp_path (Path): Le chemin du fichier à générer.
            force (bool): Si True, écrase le fichier existant. Sinon, ne fait rien s'il existe déjà.
        """

        cpp_path.parent.mkdir(parents=True, exist_ok=True)

        if cpp_path.exists() and not force:
            # print(f"⚠️ Fichier déjà existant, non modifié : {cpp_path}")
            return cpp_path

        # Écriture du fichier
        with open(cpp_path, "w") as f:
            f.write(cpp_code)
        # print(f"✅ Fichier C++ écrit : {cpp_path}")

        return cpp_path
        
    def execute(self):
        self.prepare_files()
        self.builder.execute()
        
if __name__ == "__main__":
    manager = CopyManager("decay_widths_24_2_2")
    manager.execute()