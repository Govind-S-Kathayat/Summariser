import os

import fitz  # PyMuPDF
import docx  # python-docx

from youtube_reader import read_youtube


def read_txt(path: str):

    with open(path, "r", encoding="utf-8", errors="ignore") as f:

        return f.read()


def read_pdf(path: str):

    if not os.path.exists(path):

        raise FileNotFoundError(f"PDF file not found: {path}")

    doc = fitz.open(path)

    text_parts = []

    try:

        for page in doc:

            page_text = page.get_text("text")

            if page_text.strip():

                text_parts.append(page_text)

    finally:

        doc.close()

    return "\n".join(text_parts)


def read_docx(path: str):

    if not os.path.exists(path):

        raise FileNotFoundError(f"DOCX file not found")

    doc = docx.Document(path)

    paragraphs = [

        p.text for p in doc.paragraphs

        if p.text.strip()

    ]

    return "\n".join(paragraphs)


def read_document(path: str):

    """
    Detect file type and call reader.
    Supports:
    TXT
    PDF
    DOCX
    YOUTUBE URL ⭐
    """

    # YouTube detection
    if path.startswith("http"):

        print("[INFO] Detected YouTube URL")

        return read_youtube(path)

    if not os.path.exists(path):

        raise FileNotFoundError(f"File not found: {path}")

    ext = os.path.splitext(path)[1].lower()

    if ext == ".txt":

        return read_txt(path)

    elif ext == ".pdf":

        return read_pdf(path)

    elif ext == ".docx":

        return read_docx(path)

    else:

        raise ValueError(f"Unsupported file type: {ext}")