import pytest
import types

import SetAnubis.core.BranchingRatio.domain.MartyUtil as marty_mod


def test_load_ufo_mappings_merge_and_reverse(monkeypatch):
    def fake_loader(reversed: bool):
        mapping = {"alpha0": "aEWM1", "Ve1": "Ve1"}
        return {v: k for k, v in mapping.items()} if reversed else mapping

    monkeypatch.setattr(marty_mod, "_load_ufo_mappings", fake_loader, raising=True)

    m = marty_mod.load_ufo_mappings(False)
    assert m["alpha0"] == "aEWM1" and m["Ve1"] == "Ve1"

    r = marty_mod.load_ufo_mappings(True)
    assert r["aEWM1"] == "alpha0" and r["Ve1"] == "Ve1"
