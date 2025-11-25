import os
import sys
import io
import pytest

from SetAnubis.core.DataBase.domain.ParamCardGenerator import ParamCardGenerator


def _write_fake_script(tmp_path, name="param_writer.py", content=""):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def test_patches_and_generates_in_memory(tmp_path):
    script = r'''
class ParamCardWriter:
    def __init__(self, filename, numbers=None, header="HEADER"):
        self.fsock = open(filename, "w")
        print "PY2 PRINT OK"
        self.params = list(numbers or [3, 1, 2])

    def order_param(self, a, b):
        return (a > b) - (a < b)

    def _emit(self):
        self.params.sort(self.order_param)
        for x in self.params:
            self.fsock.write("val=%d\n" % x)
        self.fsock.close()

    def __init__(self, filename, numbers=None, header="HEADER"):
        self.fsock = open(filename, "w")
        print "PY2 PRINT OK"
        self.params = list(numbers or [3, 1, 2])
        self._emit()
'''
    path = _write_fake_script(tmp_path, content=script)

    cwd0 = os.getcwd()
    sp0 = list(sys.path)

    gen = ParamCardGenerator(str(path))
    out = gen.generate_param_card(numbers=[3, 1, 2])

    assert out.strip().splitlines() == ["val=1", "val=2", "val=3"]

    assert not (tmp_path / "ignored.dat").exists()

    assert os.getcwd() == cwd0
    assert sys.path == sp0


def test_raises_runtime_error_on_missing_class(tmp_path):
    path = _write_fake_script(tmp_path, content="x = 1\n")

    gen = ParamCardGenerator(str(path))
    with pytest.raises(RuntimeError) as exc:
        gen.generate_param_card()
    assert "ParamCardWriter" in str(exc.value) or "génération du param_card" in str(exc.value)
