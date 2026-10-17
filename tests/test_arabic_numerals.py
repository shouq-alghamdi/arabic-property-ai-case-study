"""Tests for Arabic-Indic numeral normalisation.

The cases here are the ones that actually broke a production contract parser,
plus the edge cases found while fixing it.
"""

from __future__ import annotations

import pytest

from src.arabic_numerals import (
    contains_arabic_indic,
    extract_numbers,
    normalise,
    normalise_digits,
    normalise_separators,
    strip_directional_marks,
    to_arabic_indic,
    to_decimal,
)


# --- the core conversion ---------------------------------------------------


def test_arabic_indic_digits_convert():
    assert normalise_digits("٠١٢٣٤٥٦٧٨٩") == "0123456789"


def test_extended_arabic_indic_digits_convert():
    """Persian/Urdu digits. A naive map covering only U+0660-0669 misses these."""
    assert normalise_digits("۰۱۲۳۴۵۶۷۸۹") == "0123456789"


def test_mixed_digit_families_in_one_string():
    assert normalise_digits("١٢۳۴") == "1234"


def test_arabic_letters_are_untouched():
    assert normalise_digits("عقد إيجار") == "عقد إيجار"


def test_digits_inside_arabic_text():
    assert normalise_digits("عقد رقم ١٢٣٤") == "عقد رقم 1234"


def test_western_digits_pass_through_unchanged():
    assert normalise_digits("Unit 12B") == "Unit 12B"


def test_empty_string():
    assert normalise("") == ""


# --- separators ------------------------------------------------------------


def test_arabic_decimal_separator():
    assert normalise_separators("١٢٣٤٫٥٦") == "١٢٣٤.٥٦"


def test_arabic_thousands_separator():
    assert normalise_separators("٤٥٬٠٠٠") == "٤٥,٠٠٠"


def test_arabic_percent_sign():
    assert normalise_separators("٥٪") == "٥%"


def test_full_normalise_handles_digits_and_separators_together():
    assert normalise("١٢٣٤٫٥٦") == "1234.56"


# --- directional marks -----------------------------------------------------


def test_directional_marks_are_stripped():
    """PDF extraction wraps numbers in isolates. Zero-width, so invisible."""
    contaminated = "⁦١٢٣٤⁩"
    assert strip_directional_marks(contaminated) == "١٢٣٤"


def test_mark_inside_a_number_would_split_the_token_if_left_in():
    """The case that produced two wrong numbers instead of one right one."""
    contaminated = "١٢‏٣٤"
    assert extract_numbers(contaminated) == ["1234"]


def test_rtl_and_ltr_marks_both_removed():
    assert strip_directional_marks("‎5‏") == "5"


# --- extraction ------------------------------------------------------------


def test_extract_single_number_from_a_sentence():
    assert extract_numbers("الإيجار ٤٥٬٠٠٠ ريال سنوياً") == ["45000"]


def test_extract_multiple_numbers_preserves_order():
    text = "العقد من ١٤٤٦ إلى ١٤٤٧ بقيمة ٦٠٠٠٠ ريال"
    assert extract_numbers(text) == ["1446", "1447", "60000"]


def test_extract_handles_decimals():
    assert extract_numbers("المساحة ١٢٠٫٥ متر") == ["120.5"]


def test_extract_returns_empty_list_when_no_numbers():
    assert extract_numbers("عقد إيجار سكني") == []


def test_grouping_commas_are_removed_so_the_result_is_parseable():
    (value,) = extract_numbers("٤٥٬٠٠٠")
    assert float(value) == 45000.0


# --- decimal parsing -------------------------------------------------------


def test_to_decimal_parses_arabic_indic():
    assert to_decimal("١٢٣٤٫٥٦") == pytest.approx(1234.56)


def test_to_decimal_parses_grouped_amount():
    assert to_decimal("٤٥٬٠٠٠") == pytest.approx(45000.0)


def test_to_decimal_raises_rather_than_returning_zero():
    """A silent zero is the bug this module exists to prevent."""
    with pytest.raises(ValueError, match="no parseable number"):
        to_decimal("لا يوجد رقم")


def test_to_decimal_rejects_ambiguous_input():
    with pytest.raises(ValueError, match="found 2"):
        to_decimal("١٢ و ٣٤")


# --- round trip ------------------------------------------------------------


def test_to_arabic_indic_for_display():
    assert to_arabic_indic("1234") == "١٢٣٤"


def test_round_trip_is_stable():
    assert normalise_digits(to_arabic_indic("90210")) == "90210"


# --- detection -------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("١٢٣", True),
        ("۱۲۳", True),
        ("123", False),
        ("عقد", False),
        ("Unit ٥", True),
    ],
)
def test_contains_arabic_indic(text, expected):
    assert contains_arabic_indic(text) is expected


# --- realistic contract lines ----------------------------------------------


@pytest.mark.parametrize(
    "line,expected",
    [
        ("رقم العقد: ٣٣٢٢١١", ["332211"]),
        ("قيمة الإيجار السنوي: ٥٥٬٠٠٠ ريال", ["55000"]),
        ("مدة العقد: ١٢ شهر", ["12"]),
        ("تاريخ البداية: ٠١/٠٧/١٤٤٦", ["01", "07", "1446"]),
        ("المساحة: ٢٣٤٫٧٥ م٢", ["234.75", "2"]),
    ],
)
def test_contract_lines(line, expected):
    assert extract_numbers(line) == expected
