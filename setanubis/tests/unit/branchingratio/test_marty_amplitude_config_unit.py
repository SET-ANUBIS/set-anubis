import re

import pytest

from SetAnubis.core.BranchingRatio.domain.MartyAmplitudeConfig import (
    amplitude_config_suffix,
    normalize_mediator_fermion_orders,
)


def test_none_preserves_legacy_configuration():
    components = normalize_mediator_fermion_orders(None)
    assert components == ()
    assert amplitude_config_suffix(components) == ""


def test_mediator_dictionary_is_normalized_deterministically():
    first = normalize_mediator_fermion_orders(
        {"Z": [3, 0, 2, 1], "W": [2, 0, 3, 1]}
    )
    second = normalize_mediator_fermion_orders(
        {"W": [2, 0, 3, 1], "Z": [3, 0, 2, 1]}
    )

    assert first == second
    assert [component.mediators for component in first] == [("W",), ("Z",)]
    assert first[0].fermion_order == (2, 0, 3, 1)
    assert amplitude_config_suffix(first) == amplitude_config_suffix(second)


def test_tuple_key_groups_mediator_family():
    components = normalize_mediator_fermion_orders(
        {("G_W", "W"): [2, 0, 3, 1]}
    )
    assert components[0].mediators == ("G_W", "W")


def test_repeated_mediator_is_rejected():
    with pytest.raises(ValueError, match="only one amplitude component"):
        normalize_mediator_fermion_orders(
            {"W": [2, 0, 3, 1], ("G_W", "W"): [2, 0, 3, 1]}
        )


def test_invalid_fermion_order_is_rejected():
    with pytest.raises(ValueError, match="permutation"):
        normalize_mediator_fermion_orders({"W": [2, 0, 4, 1]})


def test_amplitude_suffix_is_cpp_identifier_safe():
    components = normalize_mediator_fermion_orders(
        {"W": [2, 0, 3, 1], "Z": [3, 0, 2, 1]}
    )
    suffix = amplitude_config_suffix(components)

    assert "w_z" in suffix
    assert suffix == suffix.lower()
    assert "-" not in suffix
    assert "+" not in suffix
    assert "." not in suffix
    assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", suffix)


def test_amplitude_suffix_sanitizes_mediator_punctuation():
    components = normalize_mediator_fermion_orders(
        {("G-W", "W+"): [2, 0, 3, 1]}
    )
    suffix = amplitude_config_suffix(components)

    assert suffix == suffix.lower()
    assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", suffix)
