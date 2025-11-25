import os
import subprocess
from enum import Enum
from pathlib import Path
import re

class CompilerType(Enum):
    MAKE = "MAKE"
    GCC = "GCC"

class MartyCompiler:
    def __init__(self, compiler_type: CompilerType, ampli_name : str = None):
        self.compiler_type = compiler_type
        self.project_root = Path(__file__).resolve().parents[5]
        self.libs_path = None
        if ampli_name:
            self.libs_path = self.project_root / "Assets" / "MARTY" / "MartyTemp" / "libs" / ampli_name
            self.ampli_name = ampli_name
        self.marty_lib_path = self.project_root / "External_Integration" / "MARTY" / "MARTY_INSTALL" / "lib"

        if self.libs_path == None and compiler_type == CompilerType.MAKE:
            raise ValueError("ampli_name needs to be specified for compiler if make mode.")

    def check_if_compile(self, output_binary: str) -> bool:
        if self.compiler_type == CompilerType.MAKE:
            if os.path.exists(self.libs_path / "bin" / ("example_" + self.ampli_name + ".x")):
                return True
            return False
        
        if os.path.isabs(output_binary):
            bin_path = Path(output_binary)
        else:
            bin_path = self.libs_path / output_binary
        
        # print("binpath is : ", bin_path)
        if bin_path.suffix and bin_path.suffix != ".x":
            raise ValueError(f"Expected binary path without extension, got: {bin_path.name}")

        exists = bin_path.is_file()
        executable = os.access(bin_path, os.X_OK)

        # print(f"🔍 Checking binary: {bin_path} → exists: {exists}, is_executable: {executable}")

        return exists and executable

    def compile_run(self, source_file: str, output_binary: str = None, output_dir: str = None, pattern: str = None):
        if not self.check_if_compile(output_binary):
            self.compile(source_file, output_binary)

        if self.compiler_type == CompilerType.GCC and output_dir:
            command_run = f"cd {output_dir} && ./{Path(output_binary).name}"
        else:
            bin_name = "example_" + self.ampli_name + ".x"
            command_run = f"cd {self.libs_path} && ./bin/{bin_name}"

        return self.execute_command(command_run, pattern=pattern)

    def compile(self, source_file: str, output_binary: str):
        if self.compiler_type == CompilerType.GCC:
            command = (
                f"g++ -o {output_binary} {source_file} "
                f"-L{self.marty_lib_path} "
                f"-Wl,-rpath,{self.marty_lib_path} "
                "-lmarty -lgfortran"
            )
        elif self.compiler_type == CompilerType.MAKE:
            command = f"cd {self.libs_path} && make"
        else:
            raise ValueError("Unsupported compiler type")

        return self.execute_command(command)

    def check_if_executed(self):
        if os.path.exists(self.libs_path / "script" / ("example_" + self.ampli_name + ".cpp")):
            return True
        return False
    
    def execute_command(self, command: str, pattern: str = None):
        # print(f"Executing: {command}")
        
        if self.compiler_type == CompilerType.GCC:
            is_executed = self.check_if_executed()
            if is_executed:
                return None
        result = subprocess.run(
            command, shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Command failed with return code {result.returncode}\n"
                f"stderr: {result.stderr}"
            )

        output = result.stdout
        print(output)
        if pattern:
            match = re.search(pattern, output)
            if match:
                return match.group(1)
        return None

if __name__ == "__main__":
    mc = MartyCompiler(CompilerType.MAKE, "decay_widths_24_2_2")
    
    mc.compile_run(mc.libs_path, "example_decay_widths_24_2_2.x")