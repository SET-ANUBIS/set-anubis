import re
import os
import sys
import shutil
import tempfile
import tokenize
from pathlib import Path


class ParamCardGenerator:
    def __init__(self, script_path):
        self.script_path = os.path.abspath(script_path)

    def _patch_code(self, code):
        code = self._fix_py2_prints(code)
        code = self._fix_py2_raise(code)
        code = self._fix_py2_except(code)
        code = self._fix_cmp_sort_to_key(code)
        code = self._remove_fsock_close(code)
        code = self._replace_fsock_open(code)
        return code

    def _fix_py2_prints(self, code):
        return re.sub(
            r'(?m)^(\s*)print\s+(.+?)\s*$',
            r'\1print(\2)',
            code
        )

    def _fix_py2_raise(self, code):
        return re.sub(
            r'(?m)^(\s*)raise\s+([A-Za-z_][\w\.]*)\s*,\s*(.+?)\s*$',
            r'\1raise \2(\3)',
            code
        )

    def _fix_py2_except(self, code):
        return re.sub(
            r'(?m)^(\s*)except\s+([^:]+?)\s*,\s*([A-Za-z_]\w*)\s*:',
            r'\1except \2 as \3:',
            code
        )

    def _fix_cmp_sort_to_key(self, code):
        pattern = r'(\w+)\.sort\(\s*(self\.\w+)\s*\)'
        replacement = r'\1.sort(key=__import__("functools").cmp_to_key(\2))'
        return re.sub(pattern, replacement, code)

    def _remove_fsock_close(self, code):
        return re.sub(
            r'self\.fsock\.close\(\)',
            '# self.fsock.close()  # removed by patch',
            code
        )

    def _replace_fsock_open(self, code):
        return re.sub(
            r'self\.fsock\s*=\s*open\(.*?\)',
            'self.fsock = __import__("io").StringIO()',
            code,
            flags=re.DOTALL
        )

    def _read_python_file(self, path):
        try:
            with tokenize.open(path) as f:
                return f.read(), f.encoding
        except (SyntaxError, UnicodeDecodeError):
            for enc in ("latin-1", "cp1252"):
                try:
                    with open(path, "r", encoding=enc) as f:
                        return f.read(), enc
                except UnicodeDecodeError:
                    pass
            raise

    def _write_python_file(self, path, code, encoding):
        with open(path, "w", encoding=encoding) as f:
            f.write(code)

    def _prepare_patched_tree(self):
        src_dir = os.path.dirname(self.script_path)
        script_name = os.path.basename(self.script_path)

        temp_root = tempfile.mkdtemp(prefix="ufo_py3_")
        patched_dir = os.path.join(temp_root, os.path.basename(src_dir))
        shutil.copytree(src_dir, patched_dir)

        for py_file in Path(patched_dir).rglob("*.py"):
            code, encoding = self._read_python_file(py_file)
            patched = self._patch_code(code)
            self._write_python_file(py_file, patched, encoding)

        patched_script = os.path.join(patched_dir, script_name)
        return temp_root, patched_dir, patched_script

    def generate_param_card(self, **init_kwargs):
        local_env = {}
        original_cwd = os.getcwd()
        original_sys_path = list(sys.path)

        temp_root, patched_dir, patched_script = self._prepare_patched_tree()

        try:
            if patched_dir not in sys.path:
                sys.path.insert(0, patched_dir)
            os.chdir(patched_dir)

            code, _ = self._read_python_file(patched_script)
            exec(compile(code, patched_script, "exec"), local_env)

            ParamCardWriter = local_env["ParamCardWriter"]
            writer = ParamCardWriter(filename="ignored.dat", **init_kwargs)
            return writer.fsock.getvalue()

        except Exception as e:
            raise RuntimeError(f"Erreur lors de la génération du param_card : {e}") from e

        finally:
            os.chdir(original_cwd)
            sys.path = original_sys_path
            shutil.rmtree(temp_root, ignore_errors=True)