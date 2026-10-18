import pytest

from core.params import check_all, params_errors, params_files


def test_every_params_file_is_valid():
    assert params_files()  # at least the M0 cycle params
    assert check_all() == {}


@pytest.mark.parametrize("entry", [
    {"value": 1.0, "unit": "-", "tag": "T", "tolerance": 0.1},
    {"value": 1.0, "note": "a", "GasTurb default": None},  # unquoted comma in a flow-mapping note
    {"value": 1.0, "tag": "X"},
])
def test_quantity_entry_rejects_unknown_keys_and_tags(entry):
    assert params_errors({"section": {"item": entry}})


def test_non_quantity_mappings_are_free():
    assert params_errors({"checks": {"range": {"min": 1, "max": 2, "unit": "K", "tag": "G"}},
                          "nested": [{"a": {"value": 1.0, "source": "s", "note": "n"}}]}) == []
