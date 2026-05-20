"""
Normalize city / place names before Open-Meteo geocoding.

Handles natural-language forms (e.g. Turkish "Kopenhag'a" → "Kopenhag"),
punctuation, and conservative removal of common case suffixes when attached
without a space.
"""
from __future__ import annotations

import re
import unicodedata

# Turkish & Latin-1 lookalikes → ASCII-ish fold for a last-resort API query
_ASCII_FOLD_CHARS = str.maketrans(
    {
        "ğ": "g",
        "Ğ": "G",
        "ı": "i",
        "İ": "I",
        "ş": "s",
        "Ş": "S",
        "ü": "u",
        "Ü": "U",
        "ö": "o",
        "Ö": "O",
        "ç": "c",
        "Ç": "C",
    }
)

# Conservative Turkish locative / dative / ablative etc. (≥2 chars), optional leading apostrophe
_TR_CASE_SUFFIX = re.compile(
    r"(?i)(?:'|’|ʼ)?("
    r"ya|ye|yu|yü|"
    r"da|de|dı|di|du|dü|"
    r"ta|te|tı|ti|tu|tü|"
    r"dan|den|tan|ten|"
    r"daki|deki"
    r")$"
)


def _strip_outer_junk(s: str) -> str:
    """Remove wrapping whitespace and obvious sentence punctuation/brackets."""
    if not s:
        return ""
    t = s.strip()
    t = t.strip("""'"'"''"".,!?;:()[]{}«»‹›""")
    return t.strip()


def _ascii_fold(s: str) -> str:
    if not s:
        return ""
    t = unicodedata.normalize("NFC", s).translate(_ASCII_FOLD_CHARS)
    # Normalize "İ" handling (still capital I in ASCII fold above)
    return t


def _peel_turkish_case_suffixes(s: str, max_peels: int = 2) -> list[str]:
    """Return extra variants with suffixes removed (longest stem preserved first)."""
    out: list[str] = []
    t = s
    for _ in range(max_peels):
        m = _TR_CASE_SUFFIX.search(t)
        if not m:
            break
        stem = t[: m.start()].strip()
        # Avoid mutilating very short tokens or stripping wrongly on 3-letter cities
        if len(stem) < 3:
            break
        t = stem
        if t and t not in out:
            out.append(t)
    return out


def city_name_geocode_variants(raw: str) -> list[str]:
    """
    Build an ordered list of geocoding query strings to try.
    Most likely hits first (stem before apostrophe, then cleaned full string, etc.).
    """
    if raw is None:
        return []
    s0 = _strip_outer_junk(str(raw))
    if not s0:
        return []

    ordered: list[str] = []
    seen: set[str] = set()

    def push(x: str) -> None:
        x = _strip_outer_junk(x)
        if not x:
            return
        key = x.casefold()
        if key in seen:
            return
        seen.add(key)
        ordered.append(x)

    # 1) Stem before typographic apostrophe (Turkish: Kopenhag'a, İstanbul'a)
    for sep in ("'", "\u2019", "ʼ", "`"):
        if sep in s0:
            stem = _strip_outer_junk(s0.split(sep, 1)[0])
            if stem:
                push(stem)

    # 2) Whole token after outer junk strip
    push(s0)

    # 3) Peel Turkish-style suffixes from current candidates' last forms
    bases = list(ordered)
    for b in bases:
        for p in _peel_turkish_case_suffixes(b):
            push(p)

    # 4) ASCII-folded fallbacks (helps API match "Kopenhag" / transliterated forms)
    for b in list(ordered):
        folded = _ascii_fold(b)
        if folded != b:
            push(folded)

    return ordered


__all__ = ["city_name_geocode_variants"]
