"""
Arabic-Indic numeral normalisation for Arabic document pipelines.

Why this exists
---------------
Official Arabic documents — tenancy contracts, invoices, government forms —
write numbers in Arabic-Indic digits (٠-٩, U+0660-U+0669) rather than the
Western digits (0-9) that every parser, date library, and numeric comparison in
a typical stack expects.

The failure mode is quiet and expensive. `int("١٢")` raises. `"١٢" == "12"` is
False. A date parser silently skips a field. A contract value reads as zero.
Nothing crashes loudly enough to notice in a demo; everything is wrong in
production.

This module normalises digits while leaving the surrounding Arabic text
untouched, handles the Arabic separators that travel with those digits, and is
careful about the two cases a naive `str.translate` gets wrong: Eastern Arabic
(Persian/Urdu) digits, and the directional marks that editors inject into
mixed-direction text.

Extracted from a production property-management platform where contract
parsing broke end to end on this, and rebuilt here as a standalone utility.
"""

from __future__ import annotations

import re
import unicodedata

# U+0660-U+0669 — Arabic-Indic digits. Used across the Arab world.
ARABIC_INDIC = "٠١٢٣٤٥٦٧٨٩"

# U+06F0-U+06F9 — Extended Arabic-Indic digits. Persian and Urdu.
# Visually near-identical to the above for ٤ ٥ ٦ / ۴ ۵ ۶, and a frequent
# contaminant in documents that passed through Persian-locale software.
EXTENDED_ARABIC_INDIC = "۰۱۲۳۴۵۶۷۸۹"

WESTERN = "0123456789"

# Separators that accompany Arabic-Indic digits.
ARABIC_DECIMAL_SEPARATOR = "٫"      # ٫
ARABIC_THOUSANDS_SEPARATOR = "٬"    # ٬
ARABIC_PERCENT_SIGN = "٪"           # ٪

# Directional formatting characters. Editors and PDF extractors inject these
# around numbers in mixed-direction text. They are zero-width, so they survive
# visual inspection and then break every numeric parse downstream.
DIRECTIONAL_MARKS = (
    "‎"  # LEFT-TO-RIGHT MARK
    "‏"  # RIGHT-TO-LEFT MARK
    "‪"  # LEFT-TO-RIGHT EMBEDDING
    "‫"  # RIGHT-TO-LEFT EMBEDDING
    "‬"  # POP DIRECTIONAL FORMATTING
    "‭"  # LEFT-TO-RIGHT OVERRIDE
    "‮"  # RIGHT-TO-LEFT OVERRIDE
    "⁦"  # LEFT-TO-RIGHT ISOLATE
    "⁧"  # RIGHT-TO-LEFT ISOLATE
    "⁨"  # FIRST STRONG ISOLATE
    "⁩"  # POP DIRECTIONAL ISOLATE
    "؜"  # ARABIC LETTER MARK
)

_DIGIT_MAP = str.maketrans(
    ARABIC_INDIC + EXTENDED_ARABIC_INDIC,
    WESTERN + WESTERN,
)

_MARK_MAP = {ord(c): None for c in DIRECTIONAL_MARKS}

# A number token after digit normalisation: optional sign, digits, with
# optional grouping and a single decimal part.
_NUMBER_TOKEN = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")


def strip_directional_marks(text: str) -> str:
    """Remove zero-width directional formatting characters."""
    return text.translate(_MARK_MAP)


def normalise_digits(text: str) -> str:
    """
    Convert Arabic-Indic and Extended Arabic-Indic digits to Western digits.

    Arabic letters, punctuation, and everything else are left untouched.

        >>> normalise_digits("عقد رقم ١٢٣٤")
        'عقد رقم 1234'
        >>> normalise_digits("۱۲۳")          # Persian digits
        '123'
    """
    return text.translate(_DIGIT_MAP)


def normalise_separators(text: str) -> str:
    """
    Convert Arabic numeric separators to their Western equivalents.

    The decimal separator ٫ becomes '.', the thousands separator ٬ becomes
    ',', and the Arabic percent sign ٪ becomes '%'.

        >>> normalise_separators("١٢٣٤٫٥٦")
        '١٢٣٤.٥٦'
    """
    return (
        text.replace(ARABIC_DECIMAL_SEPARATOR, ".")
        .replace(ARABIC_THOUSANDS_SEPARATOR, ",")
        .replace(ARABIC_PERCENT_SIGN, "%")
    )


def normalise(text: str, *, nfkc: bool = False) -> str:
    """
    Full normalisation pass, in the order that matters.

    Directional marks come off first — leaving them in place would split a
    number token in two and defeat every later step. Separators are converted
    before digits only because the separator characters are unaffected by the
    digit map; the order of those two is in fact independent.

    Set ``nfkc=True`` to also apply Unicode NFKC, which folds Arabic
    presentation forms (ligatures, contextual letter variants) to their
    canonical letters. This is usually right for search and comparison and
    usually wrong for anything you intend to display back to the user
    verbatim — NFKC is lossy for presentation.
    """
    out = strip_directional_marks(text)
    out = normalise_separators(out)
    out = normalise_digits(out)
    if nfkc:
        out = unicodedata.normalize("NFKC", out)
    return out


def extract_numbers(text: str) -> list[str]:
    """
    Return every number in the text as a normalised string.

    Grouping commas are removed from the result so the output is directly
    convertible:

        >>> extract_numbers("الإيجار ٤٥٬٠٠٠ ريال سنوياً")
        ['45000']
    """
    cleaned = normalise(text)
    return [m.group(0).replace(",", "") for m in _NUMBER_TOKEN.finditer(cleaned)]


def to_decimal(text: str) -> float:
    """
    Parse a single Arabic-Indic number to a float.

    Raises ``ValueError`` with the original input in the message when the text
    holds no parseable number — a silent zero here is exactly the failure this
    module exists to prevent.

        >>> to_decimal("١٢٣٤٫٥٦")
        1234.56
    """
    numbers = extract_numbers(text)
    if not numbers:
        raise ValueError(f"no parseable number in {text!r}")
    if len(numbers) > 1:
        raise ValueError(
            f"expected one number in {text!r}, found {len(numbers)}: {numbers}"
        )
    return float(numbers[0])


def to_arabic_indic(text: str) -> str:
    """
    Convert Western digits back to Arabic-Indic, for display.

    Use when rendering a value back into an Arabic document that should look
    native. Never store this form — normalise on the way in, convert on the
    way out.

        >>> to_arabic_indic("1234")
        '١٢٣٤'
    """
    return text.translate(str.maketrans(WESTERN, ARABIC_INDIC))


def contains_arabic_indic(text: str) -> bool:
    """True if the text holds any Arabic-Indic or Extended Arabic-Indic digit."""
    return any(c in ARABIC_INDIC or c in EXTENDED_ARABIC_INDIC for c in text)
