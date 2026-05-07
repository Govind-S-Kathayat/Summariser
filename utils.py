# utils.py

from typing import List
import re
import unicodedata
import string


def _normalize_unicode(text: str) -> str:
    """
    Normalize unicode so that weird PDF/encoded characters
    become more standard ASCII/Unicode forms.
    """
    if not text:
        return ""
    # NFKC: compatibility decomposition + canonical composition
    text = unicodedata.normalize("NFKC", text)
    return text


def _remove_control_chars(text: str) -> str:
    """
    Remove control characters and zero-width junk that often appear
    in copied/extracted PDF text.
    """
    # Remove all Cc (control) characters except \n and \t
    cleaned = []
    for ch in text:
        if ch in ("\n", "\t"):
            cleaned.append(ch)
        else:
            if unicodedata.category(ch) != "Cc":
                cleaned.append(ch)
    text = "".join(cleaned)

    # Remove zero-width spaces and similar
    text = re.sub(r"[\u200B-\u200F\uFEFF]", "", text)
    return text


def _collapse_whitespace(text: str) -> str:
    """
    Collapse repeated spaces / tabs / blank lines.
    """
    text = text.replace("\r", " ")
    text = text.replace("\t", " ")

    # Collapse multiple spaces
    text = re.sub(r"[ ]{2,}", " ", text)

    # Normalize line breaks: collapse more than 2 blank lines
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

    return text.strip()


def _cleanup_punctuation(text: str) -> str:
    """
    Reduce repeated punctuation and weird dot/noise patterns.
    Examples:
      "....." -> "."
      ",,,"   -> ","
      "-- - -" -> "-"
    """
    # Collapse runs of the same punctuation to 1
    text = re.sub(r"([.,;:!?\-])\1{1,}", r"\1", text)

    # Replace spaced dots like ". . . ." with "..."
    text = re.sub(r"(\.\s*){3,}", "... ", text)

    # Remove stray isolated punctuation tokens surrounded by spaces
    text = re.sub(r"\s[\'\"`´•·\-\–\—]{1}\s", " ", text)

    # Clean up leftover multiple punctuation combos like ".,", ",."
    text = re.sub(r"[.,;:!?]{2,}", ".", text)

    return text


def _is_gibberish_line(line: str) -> bool:
    """
    Heuristic: decide whether a line is mostly noise (PDF junk)
    instead of real language text.

    Rules (approx):
      - Lines that are entirely punctuation/symbols
      - Lines with very low alphabetic ratio and high punctuation ratio
      - Lines with many random dots/slashes
    """
    stripped = line.strip()
    if not stripped:
        return False  # empty line isn't gibberish

    # If it's extremely short, keep it (could be a heading)
    if len(stripped) <= 5:
        return False

    letters = sum(1 for c in stripped if c.isalpha())
    digits = sum(1 for c in stripped if c.isdigit())
    punct = sum(1 for c in stripped if c in string.punctuation)
    total = len(stripped)

    # All punctuation or nearly all non-alphanumeric
    if letters == 0 and digits == 0:
        return True

    # High punctuation ratio & low letter ratio => likely gibberish
    letter_ratio = letters / total
    punct_ratio = punct / total

    if letter_ratio < 0.25 and punct_ratio > 0.5 and total > 12:
        return True

    # Many dots/slashes etc.
    if re.search(r"[./\\|]{4,}", stripped):
        return True

    return False


def deep_clean_text(text: str) -> str:
    """
    Aggressive cleaning pass for noisy / PDF-extracted text:
      - Normalize unicode
      - Remove control chars / zero-widths
      - Collapse spaces and repeated punctuation
      - Drop lines that look like pure noise/junk
    """
    if not text:
        return ""

    text = _normalize_unicode(text)
    text = _remove_control_chars(text)

    # Basic punctuation normalization
    text = _cleanup_punctuation(text)

    # Split into lines and drop noisy ones
    lines = text.splitlines()
    clean_lines = []
    for line in lines:
        if _is_gibberish_line(line):
            continue
        clean_lines.append(line)

    cleaned = "\n".join(clean_lines)
    cleaned = _collapse_whitespace(cleaned)
    return cleaned


def clean_text(text: str) -> str:
    """
    Base cleaning for any text (non-aggressive).
    This is safe for normal text and for PDFs.
    For very noisy PDF text, call deep_clean_text() after this.
    """
    if not text:
        return ""

    text = _normalize_unicode(text)
    text = _remove_control_chars(text)
    text = _collapse_whitespace(text)
    return text


def split_into_chunks(text: str, max_chars: int = 3000) -> List[str]:
    """
    Split a long text into chunks of ~max_chars (without too ugly splits).
    Here we split by paragraphs first, then merge.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chars:
            if current:
                current += "\n\n" + para
            else:
                current = para
        else:
            if current:
                chunks.append(current)
            current = para

    if current:
        chunks.append(current)

    # Fallback: if still nothing (e.g., no paragraphs)
    if not chunks and text:
        for i in range(0, len(text), max_chars):
            chunks.append(text[i:i + max_chars])

    return chunks


def count_words(text: str) -> int:
    """
    Simple word count based on whitespace splitting.
    """
    words = text.split()
    return len(words)
