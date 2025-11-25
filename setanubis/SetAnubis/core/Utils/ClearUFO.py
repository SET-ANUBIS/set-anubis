import os
import re
import shutil
from pathlib import Path

class ClearUFO:
    def __init__(self, ufo_path):
        self.ufo_path = Path(ufo_path).resolve()
        self.output_path = self.ufo_path.parent / f"{self.ufo_path.name}_python3"

    def process(self):
        if self.output_path.exists():
            shutil.rmtree(self.output_path)
        shutil.copytree(self.ufo_path, self.output_path)

        for py_file in self.output_path.rglob("*.py"):
            self._patch_file(py_file)

    def _patch_file(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()

        original_code = code

        code = self._fix_py2_prints(code)
        code = self._fix_cmp_sort(code)
        code = self._remove_fsock_close(code)

        if code != original_code:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(code)

    def _fix_py2_prints(self, code):
        return re.sub(
            r'(?m)^(\s*)print\s+(".*?"|\'.*?\')\s*$',
            r'\1print(\2)',
            code
        )

    def _fix_cmp_sort(self, code):
        pattern = r'(\w+)\.sort\(\s*(\w+\.\w+)\s*\)'
        replacement = r'\1.sort(key=functools.cmp_to_key(\2))'

        if re.search(pattern, code):
            if 'import functools' not in code:
                code = 'import functools\n' + code

        return re.sub(pattern, replacement, code)

    def _remove_fsock_close(self, code):
        return re.sub(r'self\.fsock\.close\(\)', '# self.fsock.close()  # removed by ClearUFO', code)
