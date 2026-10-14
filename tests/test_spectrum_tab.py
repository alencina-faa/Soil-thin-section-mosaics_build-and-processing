import pytest

from stsm.spectrum_tab import clean_float


def test_clean_float_parses_decimal_comma():
    assert clean_float("12,5", field="Area") == 12.5


def test_clean_float_rejects_missing_value_with_field_name():
    with pytest.raises(ValueError, match="Area is missing"):
        clean_float(None, field="Area")


def test_clean_float_rejects_invalid_value_with_field_name():
    with pytest.raises(ValueError, match="Area must be numeric"):
        clean_float("not a number", field="Area")
