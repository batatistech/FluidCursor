"""Lightweight English/Arabic UI translations, safe in the resident process."""
import json
from functools import lru_cache
from pathlib import Path

SUPPORTED_LANGUAGES = ('en', 'ar')

@lru_cache(maxsize=1)
def _arabic():
    path = Path(__file__).resolve().parents[1] / 'locales' / 'ar.json'
    with path.open('r', encoding='utf-8') as handle:
        return json.load(handle)

def language_code(language):
    return 'ar' if language == 'ar' else 'en'

def tr(message, language='en'):
    """Return the original text when Arabic has no translation."""
    text = str(message)
    if language_code(language) != 'ar':
        return text
    dictionary = _arabic()
    if text in dictionary:
        return dictionary[text]
    if '\n' in text:
        return '\n'.join(tr(part, language) for part in text.split('\n'))
    if ': ' in text:
        first, last = text.split(': ', 1)
        if first in dictionary and last in dictionary:
            return dictionary[first] + ': ' + dictionary[last]
    return text
