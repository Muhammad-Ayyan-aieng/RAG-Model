import re


# ================================
# Main entry point
# ================================
def clean_text(text: str) -> str:
    text = _remove_null_bytes(text)
    text = _normalize_whitespace(text)
    text = _remove_repeated_special_chars(text)
    text = _fix_broken_lines(text)
    text = _remove_headers_footers(text)
    text = text.strip()
    return text


# ================================
# Internal helpers
# ================================
def _remove_null_bytes(text: str) -> str:
    return text.replace("\x00", "")


def _normalize_whitespace(text: str) -> str:
    # replace tabs with space
    text = text.replace("\t", " ")
    # collapse multiple spaces into one
    text = re.sub(r" {2,}", " ", text)
    # collapse more than 2 newlines into exactly 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _remove_repeated_special_chars(text: str) -> str:
    # remove lines that are just dashes, underscores, or equals signs
    # e.g. "--------------------" or "==============="
    text = re.sub(r"^[\-_=]{3,}\s*$", "", text, flags=re.MULTILINE)
    return text


def _fix_broken_lines(text: str) -> str:
    # PDFs often break sentences mid-line with a single newline
    # "This is a sen-\ntence" → "This is a sentence"
    # "This is a sentence\nthat continues" → "This is a sentence that continues"

    # fix hyphenated line breaks first
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # join lines that are broken mid-sentence
    # a line ending without punctuation followed by a lowercase letter = broken
    text = re.sub(r"(?<![.!?])\n(?=[a-z])", " ", text)

    return text


def _remove_headers_footers(text: str) -> str:
    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()

        # skip page numbers standing alone e.g. "- 1 -" or "1" or "Page 1"
        if re.match(r"^[-–]?\s*\d+\s*[-–]?$", stripped):
            continue
        if re.match(r"^[Pp]age\s+\d+", stripped):
            continue

        # skip very short lines that are likely artifacts
        # but keep short lines that end with punctuation (real content)
        if len(stripped) < 4 and not re.search(r"[.!?]$", stripped):
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)