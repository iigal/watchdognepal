"""
Custom Django template filters for Nepali (Bikram Sambat) date conversion.

Usage in templates:
    {% load nepali_dates %}
    {{ some_date|to_bs }}           → "फागुन २६, २०८२"
    {{ some_date|to_bs_english }}   → "Falgun 26, 2082"
"""
import datetime
from django import template
import nepali_datetime

register = template.Library()

# Nepali Unicode digits
_NEPALI_DIGITS = '०१२३४५६७८९'

# Nepali month names in Devanagari
_NEPALI_MONTHS = {
    'Baishakh': 'बैशाख',
    'Jestha': 'जेठ',
    'Ashadh': 'असार',
    'Shrawan': 'श्रावण',
    'Bhadra': 'भदौ',
    'Ashwin': 'असोज',
    'Kartik': 'कार्तिक',
    'Mangsir': 'मंसिर',
    'Poush': 'पौष',
    'Magh': 'माघ',
    'Falgun': 'फागुन',
    'Chaitra': 'चैत्र',
}


def _to_nepali_digits(text):
    """Convert ASCII digits to Nepali Unicode digits."""
    result = []
    for ch in str(text):
        if ch.isdigit():
            result.append(_NEPALI_DIGITS[int(ch)])
        else:
            result.append(ch)
    return ''.join(result)


def _convert_to_bs(value):
    """Convert a Python date/datetime to a nepali_datetime.date."""
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        value = value.date()
    if isinstance(value, datetime.date):
        try:
            return nepali_datetime.date.from_datetime_date(value)
        except (ValueError, OverflowError):
            return None
    return None


@register.filter(name='to_bs')
def to_bs(value):
    """
    Convert an AD date to Nepali BS string with Devanagari script.
    Example: datetime.date(2026, 3, 10) → "फागुन २६, २०८२"
    """
    bs = _convert_to_bs(value)
    if bs is None:
        return ''
    english_str = bs.strftime('%B %d, %Y')  # e.g. "Falgun 26, 2082"
    # Replace English month name with Nepali
    for eng, nep in _NEPALI_MONTHS.items():
        english_str = english_str.replace(eng, nep)
    # Convert digits to Nepali
    return _to_nepali_digits(english_str)


@register.filter(name='to_bs_english')
def to_bs_english(value):
    """
    Convert an AD date to Nepali BS string in English.
    Example: datetime.date(2026, 3, 10) → "Falgun 26, 2082"
    """
    bs = _convert_to_bs(value)
    if bs is None:
        return ''
    return bs.strftime('%B %d, %Y')
