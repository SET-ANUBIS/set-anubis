import os
import sys
import pytest

from SetAnubis.core.DataBase.domain.ParamCardGenerator import ParamCardGenerator


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_exec_with_local_import_and_kwargs(tmp_path):
    util = r'''
def wrap_line(x):
    return "[[%s]]" % x
'''
    _write(tmp_path, "util_mod.py", util)

    script = r'''
from util_mod import wrap_line

class ParamCardWriter:
    def order_param(self, a, b):
        return (a > b) - (a < b)

    def __init__(self, filename, title="TAG", numbers=None):
        self.fsock = open(filename, "w")
        print "Generating param card:", "title"
        self.title = title
        self.params = list(numbers or [5, 2, 4, 3])
        self.params.sort(self.order_param)
        self.fsock.write(wrap_line("TITLE=%s" % self.title) + "\n")
        for n in self.params:
            self.fsock.write(wrap_line("n=%d" % n) + "\n")
        self.fsock.close()
'''
    script_path = _write(tmp_path, "param_writer.py", script)

    gen = ParamCardGenerator(str(script_path))
    out = gen.generate_param_card(title="MYRUN", numbers=[5, 2, 4, 3])

    lines = [l.strip() for l in out.strip().splitlines()]
    assert lines[0] == "[[TITLE=MYRUN]]"
    assert lines[1:] == ["[[n=2]]", "[[n=3]]", "[[n=4]]", "[[n=5]]"]

    assert not (tmp_path / "ignored.dat").exists()
