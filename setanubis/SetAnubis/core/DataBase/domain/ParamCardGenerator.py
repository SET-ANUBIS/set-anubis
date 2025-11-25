import re
import io
import functools
import os, sys

class ParamCardGenerator:
    def __init__(self, script_path):
        self.script_path = script_path
        self.script_code = self._load_and_patch_script()

    def _load_and_patch_script(self):
        with open(self.script_path, 'r') as f:
            code = f.read()

        code = self._fix_py2_prints(code)

        code = re.sub(
            r'self\.fsock\s*=\s*open\(.*?\)',
            'import io\n        self.fsock = io.StringIO()',
            code
        )
        code = self._fix_cmp_sort_to_key(code)
        code = self._remove_fsock_close(code)
        
        return code

    def _fix_cmp_sort_to_key(self, code):
        """
        Replace: some_list.sort(self.order_param)
        by:      some_list.sort(key=functools.cmp_to_key(self.order_param))
        """
        pattern = r'(\w+)\.sort\(\s*(self\.\w+)\s*\)'
        replacement = r'\1.sort(key=functools.cmp_to_key(\2))'

        if re.search(pattern, code):
            if 'import functools' not in code:
                code = 'import functools\n' + code

        return re.sub(pattern, replacement, code)

    def _fix_py2_prints(self, code):
        return re.sub(
            r'(?m)^(\s*)print\s+(".*?"|\'.*?\')\s*$',
            r'\1print(\2)',
            code
        )

    def _remove_fsock_close(self, code):
        """
        Supress call to self.fsock.close()
        """
        return re.sub(r'self\.fsock\.close\(\)', '# self.fsock.close()  # removed by patch', code)


    def generate_param_card(self, **init_kwargs):
        local_env = {}
        script_dir = os.path.dirname(os.path.abspath(self.script_path))
        original_cwd = os.getcwd()
        original_sys_path = list(sys.path)
    
        try:
            if script_dir not in sys.path:
                sys.path.insert(0, script_dir)
            os.chdir(script_dir)
            exec(self.script_code, local_env)
            ParamCardWriter = local_env['ParamCardWriter']
            writer = ParamCardWriter(filename="ignored.dat", **init_kwargs)
            return writer.fsock.getvalue()

        except Exception as e:
            raise RuntimeError(f"Erreur lors de la génération du param_card : {e}")
        
        finally:
            os.chdir(original_cwd)
            sys.path = original_sys_path

