"""Prompt generation using Wonder Words nouns."""

from __future__ import annotations

from wonderwords import RandomWord

_WORD_GEN = RandomWord()


def random_soup_noun() -> str:
    """Return a random noun to drop into the soup prompt."""
    for _ in range(12):
        noun = _WORD_GEN.word(
            include_parts_of_speech=["nouns"],
            word_min_length=3,
            word_max_length=12,
        )
        if not isinstance(noun, str) or not noun:
            continue
        cleaned = noun.lower().strip()
        # Skip gerund-like entries that read awkwardly in the prompt.
        if cleaned.endswith("ing") and len(cleaned) > 5:
            continue
        if " " in cleaned:
            continue
        return cleaned
    return "fly"


def build_prompt(noun: str) -> str:
    return f"Waiter, there's a {noun} in my soup!"
