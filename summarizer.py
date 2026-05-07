# summarizer.py

from typing import List
import re
import string

from transformers import pipeline, AutoTokenizer
from tqdm import tqdm


# A small English stopword set for overlap filtering
STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "is", "are", "was", "were", "be", "been", "being",
    "it", "this", "that", "these", "those",
    "as", "at", "by", "from", "about", "into", "over", "after", "before",
    "not", "no", "but", "so", "such", "than", "too", "very",
    "i", "you", "he", "she", "they", "we", "him", "her", "them", "us",
    "their", "his", "hers", "its", "our", "my", "your",
}

# Patterns jo hallucinated author / news style lagte hain
HALLUCINATION_MARKERS = [
    "cnn", "bbc", "mail online", "samaritans",
    "guardian", "reuters", "daily mail",
    "new york times", "washington post",
    "columnist", "journalist", "reporter",
    "eric liu", "iliu", "mcgahey", "mcginnis",
    "professor of", "director of", "university of",
]


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _sentence_tokenize(text: str) -> List[str]:
    """
    Simple sentence splitter based on punctuation.
    """
    text = _normalize_spaces(text)
    if not text:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def _content_words(text: str) -> set:
    """
    Lowercase, remove punctuation, stopwords -> return set of content words.
    """
    text = text.lower()
    # Remove punctuation
    text = text.translate(str.maketrans("", "", string.punctuation))
    words = text.split()
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def clean_generated_summary(summary: str, source_text: str) -> str:
    """
    Post-process the model's generated summary to:
      - remove hallucinated garbage fragments
      - drop sentences that refer to fake authors / news sources
      - drop sentences that do not share enough content words
        with the source text
      - drop very short / broken sentences like "argues dr." or "- - n ."
    """
    if not summary:
        return ""

    summary = _normalize_spaces(summary)
    source_text = _normalize_spaces(source_text)

    source_tokens = _content_words(source_text)
    source_lower = source_text.lower()

    sentences = _sentence_tokenize(summary)
    cleaned_sentences: List[str] = []

    for s in sentences:
        original_s = s
        s = s.strip()
        if not s:
            continue

        s_lower = s.lower()
        words = s.split()
        word_count = len(words)

        total = len(s)
        letters = sum(1 for c in s if c.isalpha())
        punct = sum(1 for c in s if c in string.punctuation)
        spaces = sum(1 for c in s if c.isspace())
        nonspace = max(1, total - spaces)

        letter_ratio = letters / nonspace
        punct_ratio = punct / nonspace

        # Vowel check
        vowels = sum(1 for c in s if c.lower() in "aeiou")
        has_enough_vowels = vowels >= 3

        # 1) Pure junk-looking sentences hatao
        if letter_ratio < 0.5 and punct_ratio > 0.3:
            continue
        if not has_enough_vowels:
            continue

        # 2) Tiny / obviously broken sentences drop
        # e.g., "argues dr.", "modern classrooms ., es a digital .", "- - n ."
        if word_count <= 5:
            continue

        # 3) Author / news hallucinations:
        # If these markers sentence me hain but original text me nahi -> drop
        marker_hit = False
        for marker in HALLUCINATION_MARKERS:
            if marker in s_lower and marker not in source_lower:
                marker_hit = True
                break
        if marker_hit:
            continue

        # Direct patterns like "says dr", "argues dr"
        if "says dr" in s_lower or "argues dr" in s_lower:
            continue

        # 4) Lexical overlap with source: at least 3 content words common
        s_tokens = _content_words(s)
        overlap = source_tokens.intersection(s_tokens)
        if len(overlap) < 3:
            continue

        # 5) Clean repeated punctuation runs inside sentence
        # and weird endings like "- - n ."
        s = re.sub(r"[\"\'\-/]{3,}", " ", s)
        s = s.replace(" .,", ".").replace(".,", ".")
        # remove patterns like "- - n ." at end
        s = re.sub(r"-\s*-\s*[a-zA-Z]?\s*\.$", ".", s)
        s = re.sub(r"\s{2,}", " ", s).strip()

        if s:
            cleaned_sentences.append(s)
        else:
            cleaned_sentences.append(original_s)

    cleaned_text = " ".join(cleaned_sentences).strip()
    return cleaned_text


class DocumentSummarizer:
    def __init__(
        self,
        model_name: str,
        device: int = -1,  # -1 = CPU, 0 = first GPU
        summary_max_length: int = 260,
        summary_min_length: int = 120,
    ):
        """
        model_name: huggingface model for summarization
            - "t5-small"
            - "t5-base"
            - "facebook/bart-large-cnn"
        """
        self.model_name = model_name
        self.is_t5 = "t5" in model_name.lower()

        # Load tokenizer separately so we can safely truncate by token length
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

        # Clamp to a safe max length (avoid 516 > 512 warnings)
        raw_max_len = getattr(self.tokenizer, "model_max_length", 512)
        safe_max = max(32, raw_max_len - 32)
        self.max_input_tokens = min(safe_max, 512)

        # Summarization pipeline
        self.summarizer = pipeline(
            "summarization",
            model=model_name,
            tokenizer=self.tokenizer,
            device=device,
        )

        self.summary_max_length = summary_max_length
        self.summary_min_length = summary_min_length

    def _truncate_by_tokens(self, text: str) -> str:
        """
        Truncate input text so that number of tokens <= self.max_input_tokens.
        We tokenize -> truncate -> decode back to string.
        """
        if not text.strip():
            return text

        encoded = self.tokenizer(
            text,
            max_length=self.max_input_tokens,
            truncation=True,
            return_attention_mask=False,
            return_token_type_ids=False,
        )

        input_ids = encoded["input_ids"]

        truncated_text = self.tokenizer.decode(
            input_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        )
        return truncated_text

    def summarize_chunk(self, text: str) -> str:
        """
        Summarize a single chunk of text.
        Handles:
        - T5 "summarize: " prefix
        - Truncation by token length for safety
        - Post-cleaning to remove hallucinated junk / off-topic sentences
        """
        text = text.strip()
        if not text:
            return ""

        # Truncate by token length first
        truncated = self._truncate_by_tokens(text)

        # T5 models expect "summarize: " prefix
        if self.is_t5 and not truncated.lower().startswith("summarize:"):
            input_text = "summarize: " + truncated
        else:
            input_text = truncated

        # Call HF pipeline – max_length/min_length control OUTPUT length
        result = self.summarizer(
            input_text,
            max_length=self.summary_max_length,
            min_length=self.summary_min_length,
            no_repeat_ngram_size=3,
            do_sample=False,
            truncation=True,  # extra safety
        )[0]["summary_text"]

        # Clean weird garbage / unrelated / broken sentences
        cleaned = clean_generated_summary(result.strip(), truncated)
        return cleaned

    def summarize_chunks(self, chunks: List[str]) -> str:
        """
        Summarize multiple chunks and combine the summaries.
        NOTE: No second-pass compression now, so summary will be longer,
        but still controlled per chunk.
        """
        summaries = []
        for chunk in tqdm(chunks, desc="Summarizing chunks"):
            summary = self.summarize_chunk(chunk)
            if summary:
                summaries.append(summary)

        combined = "\n\n".join(summaries)
        return combined.strip()
